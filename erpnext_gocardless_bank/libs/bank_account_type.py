# ERPNext Gocardless Bank © 2024
# Author:  Ameen Ahmed
# Company: Level Up Marketing & Software Development Services
# Licence: Please refer to LICENSE file


import frappe


# [G Bank, Bank Account]
def add_account_type(name):
    if account_type_exist(name):
        return name
    
    try:
        dt = "Bank Account Type"
        (frappe.new_doc(dt)
            .update({
                "account_type": name,
                "from_gocardless": 1
            })
            .insert(ignore_permissions=True, ignore_mandatory=True))
        
        from .cache import clear_doc_cache
        
        clear_doc_cache(dt)
        return name
    except Exception as exc:
        from frappe import _
        
        from .common import store_error, log_error
        
        store_error({
            "error": "Unable to create bank account type.",
            "account_type": name,
            "exception": str(exc)
        })
        log_error(_("Unable to create bank account type \"{0}\".").format(name))
        return None


# [Bank Account, Internal]
def account_type_exist(name):
    if frappe.db.exists("Bank Account Type", name):
        return True
    
    return False