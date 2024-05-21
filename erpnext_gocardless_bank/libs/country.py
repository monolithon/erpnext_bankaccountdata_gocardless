# ERPNext Gocardless Bank © 2024
# Author:  Ameen Ahmed
# Company: Level Up Marketing & Software Development Services
# Licence: Please refer to LICENSE file


import frappe


# [Bank]
def get_country_code(country: str):
    from .cache import get_cached_value
    
    code = get_cached_value("Country", country, "code")
    if code and isinstance(code, str):
        return code.upper()
    
    return None


# [Bank]
def country_code_exists(code: str):
    return not (frappe.db.exists({
        "doctype": "Country",
        "code": code
    }) is None)