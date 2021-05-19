# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class ResCompany(models.Model):
    _inherit = "res.company"

    pg_url = fields.Char(string="API Khatu Consultation")
    pg_user = fields.Char(string="User")
    pg_password = fields.Char(string="Password")

    def get_values_consultation(self):
        if not self.pg_url:
            raise ValidationError(_("URL not found"))
        if not self.pg_user:
            raise ValidationError(_("User not found"))
        if not self.pg_password:
            raise ValidationError(_("Password not found"))
        return self.pg_url, self.pg_user, self.pg_password
