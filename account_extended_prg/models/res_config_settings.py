from odoo import models, fields

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    company_currency_id = fields.Many2one(related='company_id.currency_id', readonly=True)
    detraccion_threshold_amount = fields.Monetary(
        string='Umbral de detracción',
        related='company_id.detraccion_threshold_amount',
        currency_field='company_currency_id',
        readonly=False
    )
