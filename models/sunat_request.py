# -*- coding: utf-8 -*-
import requests
from bs4 import BeautifulSoup
from . import sunatconstants
from .sunatinfo import SunatInfo
import re

_URL_SUNAT = "https://e-consultaruc.sunat.gob.pe/cl-ti-itmrconsruc/jcrS00Alias"
_URL_SUNAT_CAPTCHA = "https://e-consultaruc.sunat.gob.pe/cl-ti-itmrconsruc/captcha?accion=random"


def sunat_request_ruc(ruc):
    session = requests.Session()
    headers = requests.utils.default_headers()
    headers[
        'User-Agent'] = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/56.0.2924.87 Safari/537.36'
    try:
        captcha_data = session.get(_URL_SUNAT_CAPTCHA, headers=headers).text
        data_ruc = {'accion': 'consPorRuc', 'nroRuc': ruc, 'numRnd': str(captcha_data)}
        response_html = session.post(url=_URL_SUNAT, data=data_ruc, headers=headers)
    except Exception:
        raise Warning("Your inquiry could not be processed")
    html_info = BeautifulSoup(response_html.content, 'html.parser')
    table_info = html_info.find_all("td", {"class": "bg"})
    data = {}
    try:
        sunat_info = SunatInfo()
        # RUC - Razon Social
        name_values = str(table_info[0].find(text=True)).split("-")
        sunat_info.ruc = name_values[0].strip()
        sunat_info.razon_social = name_values[1].strip()
        # Tipo Contribuyente
        sunat_info.tipo_contribuyente = str(table_info[1].find(text=True))
        sunat_cons = None
        if ruc[0] == '1':
            # Verificar Nuevo RUS
            nuevo_rus = str(table_info[4].find(text=True)).strip()
            if nuevo_rus == 'SI':
                sunat_cons = sunatconstants.PersonaNaturalNuevoRusConstant
            else:
                sunat_cons = sunatconstants.PersonaNaturalSinRusConstant
        elif ruc[0] == '2':
            baja = str(table_info[5].find(text=True)).strip()
            if baja == "BAJA DE OFICIO":
                sunat_cons = sunatconstants.PersonaJuridicaConstantBaja
            else:
                sunat_cons = sunatconstants.PersonaJuridicaConstant
        sunat_info.nombre_comercial = str(table_info[sunat_cons.nombre_comercial.value].find(text=True)).strip()
        sunat_info.fecha_inscripcion = str(table_info[sunat_cons.fecha_inscripcion.value].find(text=True)).strip()
        sunat_info.estado_contibuyente = str(
            table_info[sunat_cons.estado_contribuyente.value].find(text=True)).strip()
        sunat_info.condicion_contribuyente = str(
            table_info[sunat_cons.condicion_contribuyente.value].find(text=True)).strip()
        sunat_info.domicilio_fiscal = get_address_format(
            str(table_info[sunat_cons.domicilio_fiscal.value].find(text=True)).strip())
        actividad_economicas = table_info[sunat_cons.actividad_economica.value].find('select').find_all('option')
        actividades = []
        for item_act in actividad_economicas:
            actividad_economica = str(item_act.find(text=True)).split("-")
            actividades.append("{0} - {1} - {2}".format(actividad_economica[0].strip(),
                                                        actividad_economica[1].strip(),
                                                        actividad_economica[2].strip()))
        sunat_info.actividad_economica = actividades
        sunat_info.serialize()
        data["success"] = True
        data["value"] = sunat_info.serialize()
    except Exception as ex:
        data["success"] = False
        data["error"] = "Por favor intente nuevamente en unos instantes."
    return data


def get_address_format(address):
    address_y = address.split("-")
    distrito = False
    provincia = False
    departamento = False
    if len(address_y) == 3:
        distrito = address_y[-1].strip().title()
        provincia = address_y[-2].strip().title()
        # direccion = address_y[-3].strip().rsplit(" ", 1)[0].strip()
        # departamento = address_y[-3].strip().rsplit(" ", 1)[1].strip().title()
        direccion = address_y[-3].strip().rsplit(" ", 1)[0].strip()
        departamento = address_y[-3].strip().rsplit(" ", 1)[1].strip().title()
    else:
        direccion = address.strip()
    return {
        "direccion": direccion,
        "distrito": distrito,
        "provincia": provincia,
        "departamento": departamento
    }
