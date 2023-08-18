# ERPNext Nordigen © 2023
# Author:  Ameen Ahmed
# Company: Level Up Marketing & Software Development Services
# Licence: Please refer to LICENSE file


import json

import frappe
from frappe import _

from erpnext_nordigen import __production__
from .log_formatter import get_logger


_LOGGER_ERROR = None
_LOGGER_INFO = None
if not __production__:
    _LOGGER_ERROR = get_logger("error")
    _LOGGER_INFO = get_logger("info")


def log_error(data):
    if _LOGGER_ERROR:
        _LOGGER_ERROR.error(data)
    else:
        error({"error": data}, False, "xAHN9W67LP")


def log_info(data):
    if _LOGGER_INFO:
        _LOGGER_INFO.info(data)
    else:
        error({"info": data}, False, "Uw5jTfr8VQ")


def error(text, throw=True, code=None, ref_doctype=None, ref_name=None):
    if not isinstance(text, str):
        text = to_json(text)
        if not isinstance(text, str):
            try:
                text = str(text)
            except Exception:
                text = None
    
    if text:
        if not code:
            code = frappe.generate_hash(text)
        cache = frappe.cache().get_value(code, expires=True)
        if not cache:
            frappe.cache().set_value(code, "true", expires_in_sec=180)
            frappe.log_error(_("Nordigen"), text, ref_doctype, ref_name)
            if throw:
                frappe.throw(text, title=_("Nordigen"))


def parse_json(data, default=None):
    if not isinstance(data, str):
        return data
    if default is None:
        default = data
    try:
        return json.loads(data)
    except Exception:
        return default


def to_json(data, default=None):
    if isinstance(data, str):
        return data
    if default is None:
        default = data
    try:
        return json.dumps(data)
    except Exception:
        return default


def to_pretty_json(data, default=None):
    if isinstance(data, str):
        return data
    if default is None:
        default = data
    try:
        return json.dumps(data, indent=4)
    except Exception:
        return default