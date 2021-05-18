# -*- coding: utf-8 -*-
import requests
import base64


def _call_api(url, _auth):
    _headers = {"Authorization": "Basic " + _auth}
    return requests.get(url=url,
                        headers=_headers)


def _parse_response(response):
    if response.status_code != 200:
        res_json = response.json()
        return {"success": False, "error": res_json["error_descrip"]}
    return response.json()


def get_data_ruc(ruc, url, user, token):
    _url = url + '/ruc/' + ruc
    _auth = ('', token)
    usrPass = user + ":" + token
    b64Auth = base64.b64encode(usrPass.encode()).decode()
    response = _call_api(_url, b64Auth)
    return _parse_response(response)
