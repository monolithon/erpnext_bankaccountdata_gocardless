# ERPNext Gocardless Bank © 2024
# Author:  Ameen Ahmed
# Company: Level Up Marketing & Software Development Services
# Licence: Please refer to LICENSE file


import frappe


# [Bank, Bank Transaction, Currency, Schedule]
def get_cache(dt: str, key: str, expires: bool=False):
    return frappe.cache().get_value(f"{dt}-{key}", expires=expires)


# [Bank, Bank Transaction, Currency]
def set_cache(dt: str, key: str, data, expiry: int=None):
    frappe.cache().set_value(f"{dt}-{key}", data, expires_in_sec=expiry)


# [Bank Transaction]
def del_cache(dt: str, key: str):
    frappe.cache().delete_key(f"{dt}-{key}")


# [Bank, System, Internal]
def get_cached_doc(dt: str, name: str=None, for_update: bool=False):
    if name is None:
        name = dt
    if for_update:
        clear_doc_cache(dt, name)
    if dt != name and not frappe.db.exists(dt, name):
        return None
    
    return frappe.get_cached_doc(dt, name, for_update=for_update)


# [G Bank, G Setting, Bank, Bank Account, Bank Account Type, Bank Transaction, Currency, Internal]
def clear_doc_cache(dt: str, name: str=None):
    frappe.cache().delete_keys(dt)
    frappe.clear_cache(doctype=dt)
    if name is None:
        name = dt
    frappe.clear_document_cache(dt, name)


# [Bank, Company, Country]
def get_cached_value(dt: str, name: str, field: str | list, raw: bool=False):
    if not field or not isinstance(field, (str, list)):
        return None
    
    doc = get_cached_doc(dt, name)
    if not doc:
        return None
    
    if isinstance(field, str):
        return doc.get(field)
    
    values = {}
    for f in field:
        if f and isinstance(f, str):
            values[f] = doc.get(f)
    
    if not values:
        return None
    
    return values if raw else frappe._dict(values)