# ERPNext Gocardless Bank © 2024
# Author:  Ameen Ahmed
# Company: Level Up Marketing & Software Development Services
# Licence: Please refer to LICENSE file


import frappe


# [Bank Transaction]
def is_customer_exist(name: str):
    if frappe.db.exists("Customer", {"customer_name": name}):
        return True
    
    return False


# [Bank Transaction]
def add_new_customer(name: str, group: str, territory: str):
    from .cache import clear_doc_cache
    
    try:
        dt = "Customer"
        doc = frappe.new_doc(dt)
        doc.update({
            "customer_name": name,
            "customer_type": "Individual",
            "customer_group": group,
            "territory": territory,
            "from_gocardless": 1
        })
        doc.insert(ignore_permissions=True, ignore_mandatory=True)
        clear_doc_cache(dt)
        return {"dt": dt, "name": doc.name}
    except Exception as exc:
        return {"error": str(exc)}


# [Bank Transaction]
def get_customer_name(name: str):
    dt = "Customer"
    name = frappe.db.get_value(dt, {"customer_name": name}, "name")
    if name and isinstance(name, list):
        name = name.pop(0)
    
    if not name or not isinstance(name, str):
        return None
    
    return {"dt": dt, "name": name}


# [Bank Transaction]
def set_customer_bank_account(name: str, account: str):
    from .cache import clear_doc_cache
    
    dt = "Customer"
    frappe.flags.from_gocardless_update = 1
    frappe.db.set_value(dt, name, "default_bank_account", account)
    frappe.flags.pop("from_gocardless_update", 0)
    clear_doc_cache(dt)