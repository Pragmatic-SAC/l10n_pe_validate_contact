from odoo import models, fields, api, _
from odoo.exceptions import UserError
from html import escape as html_escape
import logging
import tempfile
import re
import requests
from odoo.tools.safe_eval import safe_eval
from datetime import date, datetime

try:
    import openpyxl
except ImportError:
    openpyxl = None

_logger = logging.getLogger(__name__)


class ExcelRuleConfig(models.Model):
    _name = "excel.rule.config"
    _description = "Configuración de Excel para Reglas y Notificaciones"

    name = fields.Char(string="Nombre", required=True)
    drive_url = fields.Char(
        string="URL de Google Drive",
        help="Enlace al Excel en Google Drive (hoja de cálculo o archivo .xlsx).",
    )

    header_ids = fields.One2many(
        "excel.rule.header", "config_id", string="Encabezados"
    )

    group_by_header_id = fields.Many2one(
        "excel.rule.header",
        string="Agrupar por campo (responsable)",
        domain="[('config_id', '=', config_id), ('can_be_group_by', '=', True)]",
        help="Si se define, esta regla agrupará los correos por este encabezado. "
             "Si está vacío, se usará el campo de agrupación definido en la configuración.",
    )

    rule_ids = fields.One2many(
        "excel.rule", "config_id", string="Reglas"
    )

    email_subject = fields.Char(
        string="Asunto del correo",
        default="Resumen de tareas pendientes",
        help="Asunto base para los correos que se envíen.",
    )
    email_body_intro = fields.Text(
        string="Texto introductorio del correo",
        default="Hola,\n\nEstas son tus tareas pendientes:",
        help="Texto que se mostrará al inicio del correo.",
    )

    line_template = fields.Text(
        string="Plantilla de línea",
        help="Usa ${NombreEncabezado} para insertar valores de cada fila.",
        default="-",
    )
    email_body_outro = fields.Text(
        string="Texto de cierre del correo"
    )

    def _eval_logic_expression_for_row(self, rule, row_index, matches_by_code):
        """
        Evalúa rule.dependency_logic para la fila row_index.

        - matches_by_code: dict { '1': set(idx), '2': set(idx), ... }
        - row_index: índice de la fila en la lista rows.
        - rule: excel.rule que tiene dependency_logic.

        Sintaxis esperada: (1o2) y (3o4)
        donde:
          - números = códigos de regla
          - 'y' = AND
          - 'o' = OR
        """
        expr = (rule.dependency_logic or "").strip()
        if not expr:
            return True

        import re

        expr_raw = expr.replace(" ", "").lower()
        expr_bool = expr_raw.replace("y", " and ").replace("o", " or ")

        codes_in_expr = set(re.findall(r'\d+', expr_bool))

        context = {}
        for code in codes_in_expr:
            var_name = f"code_{code}"
            context[var_name] = row_index in matches_by_code.get(code, set())

        def repl(m):
            code = m.group(0)
            return f"code_{code}"

        expr_py = re.sub(r'\d+', repl, expr_bool)

        try:
            result = safe_eval(expr_py, context, locals_dict=None)
        except Exception as e:
            raise UserError(_(
                "Error al evaluar la expresión lógica '%s' en la regla '%s': %s"
            ) % (rule.dependency_logic, rule.name, e))

        return bool(result)

    def _format_text_preserve_newlines(self, text):
        """Convierte saltos de línea a <br> y escapa HTML."""
        if not text:
            return ""
        from html import escape as html_escape
        return html_escape(text).replace("\n", "<br>")

    def _render_line_from_template(self, row_dict):
        """Rellena la plantilla de línea usando los valores de la fila del Excel.
        row_dict: dict {header_name: value}
        """
        self.ensure_one()
        template = self.line_template or "- ${Actividad}"

        def replacer(match):
            key = match.group(1).strip()
            val = row_dict.get(key)
            return "" if val is None else str(val)

        return re.sub(r"\$\{([^}]+)\}", replacer, template)

    @api.model
    def _check_openpyxl(self):
        if openpyxl is None:
            raise UserError(
                _("El módulo 'openpyxl' no está instalado en el servidor. "
                  "Instálalo con 'pip install openpyxl'.")
            )

    def action_read_headers(self):
        """Lee el archivo Excel en Drive y crea los encabezados (primera fila)."""
        self.ensure_one()
        self._check_openpyxl()

        file_path = self._download_excel_to_tempfile()

        try:
            wb = openpyxl.load_workbook(file_path, read_only=True)
            sheet = wb.active
            first_row = next(sheet.iter_rows(min_row=1, max_row=1, values_only=True))
            headers = [cell for cell in first_row if cell]
        except Exception as e:
            _logger.exception("Error leyendo Excel: %s", e)
            raise UserError(_("No se pudo leer el archivo Excel desde Drive. Revisa el formato."))

        self.header_ids.unlink()
        for seq, header in enumerate(headers, start=1):
            self.env["excel.rule.header"].create({
                "config_id": self.id,
                "name": header,
                "sequence": seq,
            })

    def _get_download_url_from_drive(self):
        """Construye una URL de descarga directa a partir de un enlace de Drive/Sheets."""
        self.ensure_one()
        if not self.drive_url:
            raise UserError(_("Debes indicar una URL de Google Drive."))

        url = self.drive_url.strip()
        if "export?format=xlsx" in url:
            return url

        m = re.search(r"/spreadsheets/d/([^/]+)", url)
        if m:
            file_id = m.group(1)
            return f"https://docs.google.com/spreadsheets/d/{file_id}/export?format=xlsx"

        m = re.search(r"/file/d/([^/]+)", url)
        if m:
            file_id = m.group(1)
            return f"https://drive.google.com/uc?export=download&id={file_id}"

        return url

    def _download_excel_to_tempfile(self):
        """Descarga el Excel desde Google Drive a un archivo temporal y devuelve la ruta."""
        self.ensure_one()
        self._check_openpyxl()

        download_url = self._get_download_url_from_drive()
        _logger.info("Descargando Excel desde URL: %s", download_url)

        try:
            resp = requests.get(download_url, timeout=60)
            resp.raise_for_status()
        except Exception as e:
            _logger.exception("Error descargando el archivo desde Google Drive: %s", e)
            raise UserError(_("No se pudo descargar el archivo desde la URL de Drive. "
                              "Verifica que el enlace sea público o compartido correctamente."))

        if not resp.content:
            raise UserError(_("La respuesta de la URL de Drive está vacía."))

        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
            tmp.write(resp.content)
            tmp.flush()
            return tmp.name

    def _read_excel_rows(self):
        """Devuelve (headers, rows) donde:
           - headers: lista de nombres de columna
           - rows: lista de dicts {header: valor}
        """
        self.ensure_one()
        self._check_openpyxl()

        file_path = self._download_excel_to_tempfile()

        try:
            wb = openpyxl.load_workbook(file_path, read_only=True, data_only=True)
            sheet = wb.active

            first_row = next(sheet.iter_rows(min_row=1, max_row=1, values_only=True))
            headers = [cell for cell in first_row]

            rows = []
            for row in sheet.iter_rows(min_row=2, values_only=True):
                row_dict = {}
                for idx, header in enumerate(headers):
                    if header:
                        row_dict[header] = row[idx]
                if any(row_dict.values()):
                    rows.append(row_dict)
        except Exception as e:
            _logger.exception("Error leyendo Excel: %s", e)
            raise UserError(_("No se pudieron leer las filas del archivo Excel descargado."))

        return headers, rows

    def action_execute_rules_send_emails(self):
        """
        Aplica las reglas sobre el Excel y envía correos.

        - Cada regla se evalúa de forma independiente con match_row().
        - Si varias reglas tienen el MISMO name (ej. "VALIDACIONES"),
          se unen sus resultados en UN solo correo por (nombre_regla, email).
        - No se repiten líneas dentro del mismo correo.
        - Si la regla tiene dependency_logic, la fila además debe cumplir
          esa expresión lógica basada en códigos de reglas.
        """
        self.ensure_one()
        if not self.rule_ids:
            raise UserError(_("No hay reglas configuradas."))

        headers, rows = self._read_excel_rows()

        active_rules = self.rule_ids.filtered(lambda r: r.active and r.send_email)
        if not active_rules:
            raise UserError(_("No hay reglas activas con envío de correo."))

        Mail = self.env["mail.mail"]

        matches_by_rule = {rule.id: set() for rule in active_rules}

        for idx, row in enumerate(rows):
            for rule in active_rules:
                if rule.match_row(row):
                    matches_by_rule[rule.id].add(idx)

        import re as _re
        matches_by_code = {}
        for rule in active_rules:
            if rule.code:
                numeric = "".join(_re.findall(r'\d+', rule.code)) or rule.code
                if numeric:
                    matches_by_code.setdefault(numeric, set()).update(
                        matches_by_rule.get(rule.id, set())
                    )

        rows_by_rule_name_email = {}

        for idx, row in enumerate(rows):
            for rule in active_rules:
                if idx not in matches_by_rule.get(rule.id, set()):
                    continue

                if rule.dependency_logic:
                    if not self._eval_logic_expression_for_row(rule, idx, matches_by_code):
                        continue

                group_header = rule.group_by_header_id or self.group_by_header_id

                if not group_header:
                    continue

                group_header_name = group_header.name
                responsable_value = row.get(group_header_name)
                if not responsable_value:
                    continue

                email_to = str(responsable_value).strip()
                if not email_to:
                    continue

                key = (rule.name, email_to)
                rows_by_rule_name_email.setdefault(key, set()).add(idx)

        for (rule_name, email_to), row_indexes in rows_by_rule_name_email.items():
            if not row_indexes:
                continue

            lines = []
            seen_lines = set()

            for idx in sorted(row_indexes):
                r = rows[idx]
                line = self._render_line_from_template(r)
                if line and line not in seen_lines:
                    seen_lines.add(line)
                    lines.append(line)

            if not lines:
                continue

            intro = self._format_text_preserve_newlines(self.email_body_intro or "")
            outro = self._format_text_preserve_newlines(self.email_body_outro or "")
            items_html = "".join(f"<li>{html_escape(l)}</li>" for l in lines)

            subject = self.email_subject or "Resumen de tareas"
            subject = f"{subject} - {rule_name}"

            body_html = f"<p>{intro}</p><ul>{items_html}</ul>"
            if outro:
                body_html += f"<p>{outro}</p>"

            mail_values = {
                "subject": subject,
                "body_html": body_html,
                "email_to": email_to,
            }
            mail = Mail.create(mail_values)
            mail.send()


class ExcelRuleHeader(models.Model):
    _name = "excel.rule.header"
    _description = "Encabezado de Excel"
    _order = "sequence, id"

    name = fields.Char(string="Nombre de encabezado", required=True)
    sequence = fields.Integer(string="Secuencia", default=10)
    config_id = fields.Many2one(
        "excel.rule.config", string="Configuración", ondelete="cascade"
    )

    can_be_group_by = fields.Boolean(
        string="Usar para agrupar",
        help="Marcar si este encabezado puede usarse como campo para agrupar (por ejemplo, responsable).",
    )
    can_be_filter = fields.Boolean(
        string="Usar en filtros",
        help="Marcar si este encabezado puede usarse en reglas de filtrado.",
        default=True,
    )


class ExcelRule(models.Model):
    _name = "excel.rule"
    _description = "Regla para filtrar filas del Excel"

    name = fields.Char(string="Nombre de la regla", required=True)
    code = fields.Char(
        string="Código",
        help="Identificador corto de la regla (ej: 1, 2, A, B). "
             "Este código es el que se usa en las expresiones lógicas.",
    )

    config_id = fields.Many2one(
        "excel.rule.config",
        string="Configuración",
        ondelete="cascade",
        required=True,
    )

    header_id = fields.Many2one(
        "excel.rule.header",
        string="Campo (encabezado)",
        domain="[('config_id', '=', config_id), ('can_be_filter', '=', True)]",
        required=True,
    )

    group_by_header_id = fields.Many2one(
        "excel.rule.header",
        string="Agrupar por campo (responsable)",
        domain="[('config_id', '=', config_id), ('can_be_group_by', '=', True)]",
        help=(
            "Si se define, esta regla agrupará los correos por este encabezado. "
            "Si está vacío, se usará el campo de agrupación definido en la configuración."
        ),
    )

    operator = fields.Selection(
        [
            ("=", "Igual a"),
            ("!=", "Distinto de"),
            ("contains", "Contiene"),
            ("not_contains", "No contiene"),
            ("in", "En lista"),
            ("not_in", "No en lista"),
        ],
        string="Condición",
        required=True,
        default="=",
    )

    value = fields.Char(
        string="Valor",
        help="Valor contra el cual se comparará el contenido de la celda.",
    )

    active = fields.Boolean(string="Activo", default=True)
    send_email = fields.Boolean(
        string="Usar para envío de correo",
        default=True,
        help="Si está marcado, esta regla participa para decidir si una fila se incluye en los correos.",
    )

    dependency_ids = fields.Many2many(
        "excel.rule",
        "excel_rule_dependency_rel2",
        "rule_id",
        "dependency_id",
        string="Reglas dependientes",
        help=(
            "Otras reglas que se combinan con esta a nivel lógico. "
            "Solo es informativo, la lógica real se lee de la expresión."
        ),
    )

    dependency_logic = fields.Char(
        string="Expresión lógica",
        help=(
            "Expresión usando códigos de regla, 'y' (AND), 'o' (OR) y paréntesis.\n"
            "Ejemplo: (1o2) y (3o4)"
        ),
    )

    def _normalize_str(self, v):
        """Normaliza el valor para comparaciones tolerantes."""
        if v is None:
            return ""
        if isinstance(v, (datetime, date)):
            v = v.strftime("%d/%m/%Y")
        else:
            v = str(v)
        v = v.replace("\xa0", " ")
        v = v.replace("\u200b", "")
        v = v.strip().lower()
        return v

    def match_row(self, row_dict):
        """Evalúa si esta regla se cumple para una fila dada del Excel."""
        self.ensure_one()
        header_name = self.header_id.name
        cell_value = row_dict.get(header_name)

        cell_str = self._normalize_str(cell_value)
        rule_str = self._normalize_str(self.value)

        if self.operator == "=":
            return cell_str == rule_str

        elif self.operator == "!=":
            return cell_str != rule_str

        elif self.operator == "contains":
            return rule_str in cell_str

        elif self.operator == "not_contains":
            return rule_str not in cell_str

        elif self.operator in ("in", "not_in"):
            parts = [self._normalize_str(p) for p in (self.value or "").split(",") if p.strip()]
            in_list = cell_str in parts
            return in_list if self.operator == "in" else not in_list

        return False
