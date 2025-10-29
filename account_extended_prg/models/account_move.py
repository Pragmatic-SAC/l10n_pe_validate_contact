# -*- coding: utf-8 -*-
from odoo import models, api, fields, _
from odoo.tools.float_utils import float_compare
from odoo.tools.misc import formatLang

# -------- Helpers --------
def _is_export_fpos(fpos):
    """Detecta posición fiscal de exportación por nombre (flexible)."""
    if not fpos:
        return False
    name = (fpos.display_name or fpos.name or "").upper()
    return "EXTRANJERO" in name or "EXPORT" in name


def _is_detraction_product(product):
    """Ajusta al campo real que uses para marcar detracción en productos."""
    for fname in ("l10n_pe_withhold_code", "l10n_pe_detraction_subject", "detraction_ok"):
        if hasattr(product, fname) and getattr(product, fname):
            return True
    return False


# -------- Umbral en compañía --------
# class ResCompany(models.Model):
#     _inherit = "res.company"
#
#     detraccion_threshold_amount = fields.Monetary(
#         string="Umbral de detracción",
#         help=(
#             "Si el total de la factura (moneda de la compañía) es ≥ a este valor y hay "
#             "productos sujetos a detracción, se aplicará la operación 1001."
#         ),
#         currency_field="currency_id",
#         default=700,
#     )


# -------- Lógica en factura --------
class AccountMove(models.Model):
    _inherit = "account.move"

    # === Decisor central ===
    def _decision_for_move(self):
        """
        Devuelve {move.id: {'code': '0201'|'1001'|'0101', 'show_alert': bool, 'msg': str}}
        Reglas:
          - Exportación => 0201 (sin importar total).
          - No exportación:
              * si hay producto sujeto a detracción y total ≥ umbral => 1001 + alerta
              * en cualquier otro caso => 0101 (venta nacional)
        """
        out = {}
        for move in self:
            code = "0101"  # default venta nacional
            show_alert = False
            msg = ""

            if move.move_type != "out_invoice":
                out[move.id] = {'code': False, 'show_alert': False, 'msg': ""}
                continue

            # 1) Exportación manda
            if _is_export_fpos(getattr(move.partner_id, "property_account_position_id", False)):
                code = "0201"
                out[move.id] = {'code': code, 'show_alert': False, 'msg': ""}
                continue

            # 2) Detracción por total y producto
            threshold = float(getattr(move.company_id, "detraccion_threshold_amount", 0.0) or 0.0)
            has_detraction_product = any(
                l.product_id and _is_detraction_product(l.product_id)
                for l in move.invoice_line_ids
            )
            if threshold > 0 and has_detraction_product:
                currency = move.company_id.currency_id
                if float_compare(
                    move.amount_total_signed, threshold, precision_rounding=currency.rounding
                ) >= 0:
                    code = "1001"
                    show_alert = True
                    # Mensaje en texto plano para ventanita onchange
                    msg = _(
                        "La venta está sujeta a detracción por superar el umbral.\n"
                        "Cliente: %(partner)s\n"
                        "Monto: %(amount)s  (umbral: %(th)s)"
                    ) % {
                        "partner": move.partner_id.display_name,
                        "amount": formatLang(self.env, move.amount_total_signed, currency_obj=currency),
                        "th": formatLang(self.env, threshold, currency_obj=currency),
                    }
                else:
                    code = "0101"  # revertir a venta nacional si bajó del umbral

            out[move.id] = {'code': code, 'show_alert': show_alert, 'msg': msg}
        return out

    # === ONCHANGE: reflejar código en vivo y mostrar alerta (no bloqueante) cuando aplique ===
    @api.onchange(
        'invoice_line_ids',
        'invoice_line_ids.quantity',
        'invoice_line_ids.price_unit',
        'invoice_line_ids.tax_ids',
    )
    def _onchange_update_pe_operation_live(self):
        for move in self:
            if move.move_type != 'out_invoice':
                continue

            decision = move._decision_for_move().get(move.id, {})
            desired = decision.get('code')

            # Cambiar el selector en UI sin esperar a guardar
            if desired and move.l10n_pe_edi_operation_type != desired:
                move.l10n_pe_edi_operation_type = desired

            # Mostrar ventanita de "ALERTA" SOLO cuando aplica detracción
            if decision.get('show_alert') and decision.get('msg'):
                return {
                    'warning': {
                        'title': _("ALERTA"),
                        'message': decision['msg'],
                    }
                }
        return

    # === GUARDAR: aplicar definitivamente + nota en chatter (no bloquea) ===
    def _apply_code_and_notify_on_save(self):
        decisions = self._decision_for_move()
        for move in self:
            d = decisions.get(move.id, {})
            desired = d.get('code')
            if desired and move.l10n_pe_edi_operation_type != desired:
                move.with_context(bypass_pe_op_type=True).write({
                    'l10n_pe_edi_operation_type': desired
                })

            # Registro informativo en chatter (la alerta visual ya se mostró en onchange)
            if d.get('show_alert') and d.get('msg'):
                move.message_post(body=d['msg'], subtype_xmlid="mail.mt_note")

    @api.model
    def create(self, vals_list):
        single = isinstance(vals_list, dict)
        vals_list = [vals_list] if single else vals_list
        recs = super().create(vals_list)
        if not self.env.context.get('bypass_pe_op_type'):
            recs.with_context(bypass_pe_op_type=True)._apply_code_and_notify_on_save()
        return recs if not single else recs[0]

    def write(self, vals):
        res = super().write(vals)
        if not self.env.context.get('bypass_pe_op_type'):
            self.with_context(bypass_pe_op_type=True)._apply_code_and_notify_on_save()
        return res

