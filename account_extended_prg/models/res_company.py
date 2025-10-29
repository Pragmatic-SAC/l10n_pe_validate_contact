from odoo import models, fields

class ResCompany(models.Model):
    _inherit = 'res.company'

    detraccion_threshold_amount = fields.Monetary(
        string='Umbral de detracción',
        currency_field='currency_id',
        default=700.0,
        help="Umbral (moneda de la compañía) para mostrar alerta informativa de detracción al confirmar facturas."
    )
