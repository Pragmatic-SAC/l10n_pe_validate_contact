# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from .sunat_request import sunat_request_ruc

import unicodedata


def strip_accents(s):
    return ''.join(c for c in unicodedata.normalize('NFD', s)
                   if unicodedata.category(c) != 'Mn')


class L10n_peResCityDistrict(models.Model):
    _inherit = "l10n_pe.res.city.district"

    name_unacent = fields.Char(string="Unacent Name", store=True, compute="_compute_name_unacent")

    @api.depends("name")
    def _compute_name_unacent(self):
        for district in self:
            district.name_unacent = strip_accents(district.name)


class ResCity(models.Model):
    _inherit = "res.city"

    name_unacent = fields.Char(string="Unacent Name", store=True, compute="_compute_name_unacent")

    @api.depends("name")
    def _compute_name_unacent(self):
        for city in self:
            city.name_unacent = strip_accents(city.name)


class ResCountryState(models.Model):
    _inherit = "res.country.state"

    name_unacent = fields.Char(string="Unacent Name", store=True, compute="_compute_name_unacent")

    @api.depends("name")
    def _compute_name_unacent(self):
        for state in self:
            state.name_unacent = strip_accents(state.name)
