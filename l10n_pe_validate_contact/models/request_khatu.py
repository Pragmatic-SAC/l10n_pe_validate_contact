# -*- coding: utf-8 -*-
import requests
import base64


def _call_api(url, token):
    _headers = {"Authorization": "Bearer " + token}
    return requests.get(url=url,
                        headers=_headers)


def _parse_response(response):
    if response.status_code != 200:
        res_json = response.json()
        return {"success": False, "error": res_json["error_descrip"]}
    return response.json()


def get_data_ruc(url, token):
    response = _call_api(url, token)
    return _parse_response(response)
