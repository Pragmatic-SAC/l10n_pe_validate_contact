# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from .sunat_request import sunat_request_ruc
from datetime import datetime

COLOR_STATE = {
    "active": "#239B56",
    "inactive": "#C0392B"
}
COLOR_CONDITION = {
    "active": "#239B56",
    "inactive": "#C0392B"
}


class ResPartner(models.Model):
    _inherit = "res.partner"

    commercial_name = fields.Char(string="Commercial Name")

    state = fields.Char(string='State')

    state_color = fields.Char(string="State Color")

    condition = fields.Char(string='Condition')

    condition_color = fields.Char(string="Condition Color")

    date_enrollment = fields.Date(string="Enrollment Date")

    type_of_taxpayer = fields.Char(string="Type Of Taxpayer")

    economic_assets = fields.Text(string="Economic Assets")

    def validation_sunat_contact(self):
        if self.l10n_latam_identification_type_id.l10n_pe_vat_code == "6":
            if len(self.vat) != 11:
                self.env.user.notify_danger(message=_("Please verify the vat number"))
                return False
            return True

    @api.onchange("vat", "l10n_latam_identification_type_id")
    def _onchange_sunat_validation(self):
        if self.l10n_latam_identification_type_id.id and self.vat:
            if self.validation_sunat_contact():
                data = sunat_request_ruc(self.vat)
                if not data["success"]:
                    self.env.user.notify_danger(message=data["error"])
                    return
                data = data["value"]
                self.assign_values_from_sunat(data)

    def assign_values_from_sunat(self, data):
        vals = self.get_match_address(data["domicilio_fiscal"])
        if data["razon_social"]:
            vals["name"] = data["razon_social"]
        if data["nombre_comercial"]:
            vals["commercial_name"] = data["nombre_comercial"]
        if data["tipo_contribuyente"]:
            vals["type_of_taxpayer"] = data["tipo_contribuyente"]
        if data["actividad_economica"]:
            economic_assets = ""
            for item in data["actividad_economica"]:
                economic_assets = economic_assets + str(item) + "\n"
            vals["economic_assets"] = economic_assets
        if data["domicilio_fiscal"]:
            vals["street"] = data["domicilio_fiscal"]["direccion"]
        if data["estado_contibuyente"]:
            vals["state"] = data["estado_contibuyente"]
            if vals["state"] == "ACTIVO":
                vals["state_color"] = COLOR_STATE["active"]
            else:
                vals["state_color"] = COLOR_STATE["inactive"]
        if data["condicion_contribuyente"]:
            vals["condition"] = data["condicion_contribuyente"]
            if vals["condition"] == "HABIDO":
                vals["condition_color"] = COLOR_CONDITION["active"]
            else:
                vals["condition_color"] = COLOR_CONDITION["inactive"]
        if data["fecha_inscripcion"]:
            vals["date_enrollment"] = datetime.strptime(data["fecha_inscripcion"], '%d/%m/%Y')
        self.update(vals)

    def get_match_address(self, address):
        provinces = self.env['res.city'].search(
            [('name_unacent', '=', address["provincia"]), ('state_id.name_unacent', '=', address["departamento"])],
            limit=1)
        l10n_pe_district = self.env['l10n_pe.res.city.district'].search(
            [('name_unacent', '=', address["distrito"]), ('city_id', 'in', provinces.ids)], limit=1)
        vals = {
            "country_id": False,
            "state_id": False,
            "city_id": False,
            "l10n_pe_district": False,
        }
        if l10n_pe_district.id:
            vals['l10n_pe_district'] = l10n_pe_district.id
            vals['city_id'] = l10n_pe_district.city_id.id
            vals['state_id'] = l10n_pe_district.city_id.state_id.id
            vals['country_id'] = l10n_pe_district.city_id.state_id.country_id.id
        return vals

    @api.onchange('country_id')
    def _onchange_pg_country_id(self):
        if self.city_id:
            if not self.state_id:
                return {'domain': {'city_id': []}}
        else:
            return {'domain': {'l10n_pe_district': [('city_id', '=', self.city_id.id)]}}

    @api.onchange('state_id')
    def _onchange_state_id(self):
        if self.state_id.id:
            if not self.country_id:
                self.country_id = self.state_id.country_id.id
            return {'domain': {'city_id': [('state_id', '=', self.state_id.id)]}}
        else:
            return {'domain': {'city_id': []}}

    @api.onchange('city_id')
    def _onchange_city_id(self):
        if self.city_id:
            self.city = self.city_id.name
            self.state_id = self.city_id.state_id.id
            return {'domain': {'l10n_pe_district': [('city_id', '=', self.city_id.id)]}}
        elif self._origin:
            self.city = False
            self.state_id = False
            return {'domain': {'l10n_pe_district': []}}

    @api.onchange('l10n_pe_district')
    def _onchange_pg_l10n_pe_district(self):
        if self.l10n_pe_district:
            self.city_id = self.l10n_pe_district.city_id.id
            self.zip = self.l10n_pe_district.code or ""
