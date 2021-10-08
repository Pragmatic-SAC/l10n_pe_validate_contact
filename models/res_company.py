# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class ResCompany(models.Model):
    _inherit = "res.company"

    pg_url = fields.Char(string="API DEV URL", default="https://apiperu.dev/api")
    pg_password = fields.Char(string="Token")

    def get_values_consultation(self):
        if not self.pg_url:
            raise ValidationError(_("URL not found"))
        if not self.pg_password:
            raise ValidationError(_("Token not found"))
        return self.pg_url, self.pg_password
