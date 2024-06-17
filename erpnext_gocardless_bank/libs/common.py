# ERPNext Gocardless Bank © 2024
# Author:  Ameen Ahmed
# Company: Level Up Marketing & Software Development Services
# Licence: Please refer to LICENSE file


import json

import frappe

from erpnext_gocardless_bank import (
    __module__,
    __production__
)


# [Internal]
if not __production__:
    from .logger import get_logger
    
    _LOGGER_ERROR = get_logger("error")
    _LOGGER_INFO = get_logger("info")
else:
    _LOGGER_ERROR = None
    _LOGGER_INFO = None


# [Bank, Bank Account, Bank Account Type, Gocardless, Schedule]
def store_error(data):
    if _LOGGER_ERROR:
        _LOGGER_ERROR.error(data)


# [Bank Transaction, Gocardless]
def store_info(data):
    if _LOGGER_INFO:
        _LOGGER_INFO.info(data)


# [Bank Account, Bank Account Type, Gocardless, Schedule]
def log_error(text):
    text = get_str(text)
    if text:
        from erpnext_gocardless_bank.version import is_version_lt
        
        if is_version_lt(14):
            frappe.log_error(text, __module__)
        else:
            frappe.log_error(__module__, text)


# [G Bank, G Settings, Bank, System]
def error(text: str, title: str=None):
    frappe.throw(text, title=title or __module__)


# [Gocardless]
def parse_json(data, default=None):
    if data is None:
        return default
    if not isinstance(data, str):
        return data
    try:
        return json.loads(data)
    except Exception:
        return default


# [Api, Bank Transaction, Gocardless, Schedule, Internal]
def to_json(data, default=None, pretty=False):
    if data is None:
        return default
    if isinstance(data, str):
        return data
    try:
        if pretty:
            return json.dumps(data, indent=4)
        
        return json.dumps(data)
    except Exception:
        return default


# [Internal]
def to_str(data, default=None):
    if data is None:
        return default
    if isinstance(data, str):
        return data
    try:
        return str(data)
    except Exception:
        return default


# [Internal]
def get_str(data, default=None):
    val = to_str(data)
    if val is None:
        val = to_json(data)
    if val is None:
        return default
    return val


# [Bank Transaction]
def unique_key(data=None):
    import hashlib
    import uuid
    
    return uuid.UUID(hashlib.sha256(
        to_json(data, "").encode("utf-8")
    ).hexdigest()[::2])