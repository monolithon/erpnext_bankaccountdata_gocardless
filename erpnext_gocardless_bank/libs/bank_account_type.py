# ERPNext Gocardless Bank © 2024
# Author:  Ameen Ahmed
# Company: Level Up Marketing & Software Development Services
# Licence: Please refer to LICENSE file


import frappe


# [Bank Account]
def add_account_type(name):
    dt = "Bank Account Type"
    if frappe.db.exists(dt, name):
        return 1
    
    try:
        (frappe.new_doc(dt)
            .update({"account_type": name})
            .insert(ignore_permissions=True, ignore_mandatory=True))
        
        from .cache import clear_doc_cache
        
        clear_doc_cache(dt)
        return 1
    except Exception as exc:
        from frappe import _
        
        from .common import store_error, log_error
        
        store_error({
            "error": "Unable to create bank account type.",
            "account_type": name,
            "exception": str(exc)
        })
        log_error(_("Unable to create bank account type \"{0}\".").format(name))
        return 0