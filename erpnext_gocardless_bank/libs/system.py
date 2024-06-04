# Expenses © 2024
# Author:  Ameen Ahmed
# Company: Level Up Marketing & Software Development Services
# Licence: Please refer to LICENSE file


import frappe
from frappe import _


# [Bank, Bank Account, Bank Transaction, Company, Schedule, Internal]
def settings():
    from .cache import get_cached_doc
    
    return get_cached_doc("Gocardless Settings")


# [Bank Account, Schedule, Internal]
def is_enabled():
    return settings().is_enabled


# [Gocardless JS]
@frappe.whitelist()
def get_settings():
    from erpnext_gocardless_bank import __production__
    
    doc = settings()
    return {
        "is_enabled": 1 if doc.is_enabled else 0,
        "prod": 1 if __production__ else 0
    }


# [G Bank]
def check_app_status():
    if not is_enabled():
        from .common import error
        
        error(app_disabled_message())


# [Bank Account, Bank Transaction, Internal]
def app_disabled_message():
    from erpnext_gocardless_bank import __module__
    
    return _("{0} app is disabled.").format(_(__module__))


# [Company]
def get_access_companies():
    doc = settings()
    return [v.company for v in doc.access]


# [Bank, Bank Account, Bank Transaction, Schedule]
def get_client(company: str, doc=None):
    if not doc:
        doc = settings()
    
    if not doc.is_enabled:
        return {"error": app_disabled_message()}
    
    row = None
    for v in doc.access:
        if v.company == company:
            row = v
            break
    
    if not row:
        return {
            "error": _("No Gocardless authorized access for company \"{0}\".").format(company)
        }
    
    from .access import update_access
    from .gocardless import Gocardless
    
    client = Gocardless()
    ret = update_access(row, client)
    if ret == -1:
        return {
            "error": _("Unable to gain authorized access to Gocardless for company \"{0}\".").format(company)
        }
    
    if ret:
        doc.save(ignore_permissions=True)
    else:
        client.set_access(row.access_token)
    
    return client