# -*- coding: utf-8 -*-
from odoo import models, fields, _, api
from odoo.exceptions import UserError,ValidationError

PREVENTA_NAME = "preventa"  # comparación textual, case-insensitive

def _is_preventa(project):
    return bool(project and (project.name or "").strip().lower() == PREVENTA_NAME)

def _timesheets_will_exist_after(rec, vals):
    """
    Retorna True si, tras aplicar vals['timesheet_ids'], el ticket tendrá alguna línea.
    Soporta comandos O2M: 0,1,2,5,6 (estándar de Odoo).
    """
    if 'timesheet_ids' not in vals:
        return bool(rec.timesheet_ids)

    cmds = vals.get('timesheet_ids') or []
    # estado actual
    current_ids = set(rec.timesheet_ids.ids)

    for cmd in cmds:
        if not isinstance(cmd, (list, tuple)) or not cmd:
            continue
        op = cmd[0]
        if op == 0:
            # create: habrá líneas
            return True
        elif op == 1:
            # write sobre una existente: no cambia cardinalidad
            pass
        elif op == 2:
            # unlink id
            if len(cmd) > 1:
                current_ids.discard(cmd[1])
        elif op == 5:
            # clear all
            current_ids.clear()
        elif op == 6:
            # replace por lista
            ids = set(cmd[2] or [])
            current_ids = ids

    return bool(current_ids)


class HelpdeskTicket(models.Model):
    _inherit = "helpdesk.ticket"

    task_id = fields.Many2one(required=True)

    @api.constrains('task_id')
    def _check_task_required(self):
        for rec in self:
            if not rec.task_id:
                raise ValidationError(_("El campo 'Tarea' es obligatorio en el ticket."))

    def write(self, vals):
        for rec in self:
            # proyecto final (si cambia en vals usar ese)
            project = rec.project_id
            if 'project_id' in vals:
                project = self.env['project.project'].browse(vals['project_id'])

            if _is_preventa(project) and _timesheets_will_exist_after(rec, vals):
                # Bloquear guardado con alerta
                raise UserError(
                    _("No se puede guardar: el proyecto es 'Preventa' y el ticket tiene horas registradas. "
                      "Establezca un proyecto distinto a 'Preventa' antes de guardar.")
                )
        return super().write(vals)