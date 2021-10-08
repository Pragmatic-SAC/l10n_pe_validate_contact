# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from .request_khatu import get_data_ruc

COLOR_STATE = {
    "active": "done",
    "inactive": "blocked"
}
COLOR_CONDITION = {
    "active": "done",
    "inactive": "blocked"
}


class ResPartner(models.Model):
    _inherit = "res.partner"

    # commercial_name = fields.Char(string="Commercial Name")

    state = fields.Char(string="State")

    state_color = fields.Selection(selection=[("normal", "Not Consulted"), ("done", "Active"), ("blocked", "Inactive")],
                                   string="State Color", default="normal")

    condition = fields.Char(string="Condition")

    condition_color = fields.Selection(
        selection=[("normal", "Not Consulted"), ("done", "Active"), ("blocked", "Inactive")],
        string="Condition Color", default="normal")

    # date_enrollment = fields.Date(string="Enrollment Date")
    #
    # type_of_taxpayer = fields.Char(string="Type Of Taxpayer")
    #
    # economic_assets = fields.Text(string="Economic Assets")

    def validation_sunat_contact(self):
        if self.l10n_latam_identification_type_id.l10n_pe_vat_code == "6":
            if len(self.vat) != 11:
                raise ValidationError(_("Please verify the vat number"))
            return True
        if self.l10n_latam_identification_type_id.l10n_pe_vat_code == "1":
            if len(self.vat) != 8:
                raise ValidationError(_("Please verify the vat number"))
            return True
        return False

    def get_sunat_information(self, type, vat):
        url, token = self.env.company.get_values_consultation()
        if type == "6":
            url = url + '/ruc/' + vat
        if type == "1":
            url = url + '/dni/' + vat
        data = get_data_ruc(url, token)
        return data

    @api.onchange("vat", "l10n_latam_identification_type_id")
    def _onchange_sunat_validation(self):
        if self.l10n_latam_identification_type_id.id and self.vat:
            if self.validation_sunat_contact():
                data = self.get_sunat_information(self.l10n_latam_identification_type_id.l10n_pe_vat_code, self.vat)
                if not data["success"]:
                    return
                    #raise ValidationError(data["error"])
                data = data["data"]
                if self.l10n_latam_identification_type_id.l10n_pe_vat_code == "1":
                    vals = self.assign_values_from_sunat_dni(data)
                if self.l10n_latam_identification_type_id.l10n_pe_vat_code == "6":
                    vals = self.assign_values_from_sunat_ruc(data)
                self.update(vals)

    @api.model
    def assign_values_from_sunat_dni(self, data):
        vals = {}
        if data["nombre_completo"]:
            vals["name"] = data["nombre_completo"]
        return vals

    @api.model
    def assign_values_from_sunat_ruc(self, data):
        vals = self.get_match_address(data)
        if data["nombre_o_razon_social"]:
            vals["name"] = data["nombre_o_razon_social"]
        if data["estado"]:
            vals["state"] = data["estado"]
            if vals["state"] == "ACTIVO":
                vals["state_color"] = COLOR_STATE["active"]
            else:
                vals["state_color"] = COLOR_STATE["inactive"]
        if data["condicion"]:
            vals["condition"] = data["condicion"]
            if vals["condition"] == "HABIDO":
                vals["condition_color"] = COLOR_CONDITION["active"]
            else:
                vals["condition_color"] = COLOR_CONDITION["inactive"]
        return vals

    @api.model
    def get_match_address(self, data):
        l10n_pe_district = self.env["l10n_pe.res.city.district"].search([("code", "=", data["ubigeo"][2])], limit=1)
        vals = {
            "country_id": False,
            "state_id": False,
            "city_id": False,
            "l10n_pe_district": False,
            "street": False,
        }
        if l10n_pe_district.id:
            vals["l10n_pe_district"] = l10n_pe_district.id
            vals["city_id"] = l10n_pe_district.city_id.id
            vals["state_id"] = l10n_pe_district.city_id.state_id.id
            vals["country_id"] = l10n_pe_district.city_id.state_id.country_id.id
        vals["street"] = data["direccion"]
        return vals

    @api.onchange("country_id")
    def _onchange_pg_country_id(self):
        if self.city_id:
            if not self.state_id:
                return {"domain": {"city_id": []}}
        else:
            return {"domain": {"l10n_pe_district": [("city_id", "=", self.city_id.id)]}}

    @api.onchange("state_id")
    def _onchange_state_id(self):
        if self.state_id.id:
            if not self.country_id:
                self.country_id = self.state_id.country_id.id
            return {"domain": {"city_id": [("state_id", "=", self.state_id.id)]}}
        else:
            return {"domain": {"city_id": []}}

    @api.onchange("city_id")
    def _onchange_city_id(self):
        if self.city_id:
            self.city = self.city_id.name
            self.state_id = self.city_id.state_id.id
            return {"domain": {"l10n_pe_district": [("city_id", "=", self.city_id.id)]}}
        elif self._origin:
            self.city = False
            self.state_id = False
            return {"domain": {"l10n_pe_district": []}}

    @api.onchange("l10n_pe_district")
    def _onchange_pg_l10n_pe_district(self):
        if self.l10n_pe_district:
            self.city_id = self.l10n_pe_district.city_id.id
            self.zip = self.l10n_pe_district.code or ""
