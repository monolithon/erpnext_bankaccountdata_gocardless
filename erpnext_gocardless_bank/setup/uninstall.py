# ERPNext Gocardless Bank © 2023
# Author:  Ameen Ahmed
# Company: Level Up Marketing & Software Development Services
# Licence: Please refer to LICENSE file


import frappe


def before_uninstall():
    _remove_custom_fields()
    _remove_link_from_workspace()


def _remove_custom_fields():
    fields = {
        "Bank Transaction": [
            "gocardless_transaction_info"
        ],
        "Bank Accouny": [
            "gocardless_bank_account_no"
        ],
    }
    for k, v in fields.items():
        db_doc = frappe.qb.DocType("Custom Field")
        (
            frappe.qb.from_(db_doc)
            .delete()
            .where(db_doc.dt == k)
            .where(db_doc.fieldname.isin(v))
        ).run()


def _remove_link_from_workspace():
    dt = "Workspace"
    name = "ERPNext Integrations"
    if not frappe.db.exists(dt, name):
        return 0
        
    doc = frappe.get_doc(dt, name)
    keys = ["Gocardless Settings", "Gocardless Bank", "Gocardless Sync Log"]
    found = 0
    
    for v in doc.links:
        if v.type == "Link" and v.label in keys:
            try:
                doc.links.remove(v)
                found = 1
            except Exception:
                pass
    
    if found:
        doc.save(ignore_permissions=True)