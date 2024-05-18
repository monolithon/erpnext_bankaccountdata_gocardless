# ERPNext Gocardless Bank © 2024
# Author:  Ameen Ahmed
# Company: Level Up Marketing & Software Development Services
# Licence: Please refer to LICENSE file


import frappe


# [Hooks, Install]
def after_uninstall():
    doctypes = get_doctypes()
    docs = [
        ["Custom Field", [
            "Bank-from_gocardless",
            "Bank Account-from_gocardless",
            "Bank Account Type-from_gocardless",
            "Bank Transaction-from_gocardless",
            "Currency-from_gocardless",
            "Supplier-from_gocardless",
            "Customer-from_gocardless",
            "Bank Account-gocardless_bank_account_no",
            "Bank Transaction-gocardless_transaction_info"
        ]],
        ["DocType", doctypes],
        ["Module Def", ["ERPNext Gocardless Bank"]]
    ]
    
    _remove_workspace_links(doctypes)
    
    for doc in docs:
        for name in doc[1]:
            try:
                frappe.delete_doc(
                    doc[0], name,
                    ignore_permissions=True,
                    ignore_missing=True,
                    ignore_on_trash=True,
                    delete_permanently=True
                )
            except Exception:
                pass
    
    frappe.clear_cache()


# [Install, Internal]
def get_doctypes():
    return [
        "Gocardless Bank Account",
        "Gocardless Access",
        "Gocardless Sync Log",
        "Gocardless Bank",
        "Gocardless Settings"
    ]


# [Internal]
def _remove_workspace_links(doctypes):
    dt = "Workspace"
    name = "ERPNext Integrations"
    if not frappe.db.exists(dt, name):
        return 0
    
    doc = frappe.get_doc(dt, name)
    found = 0
    for v in doc.links:
        if v.type == "Link" and v.link_to in doctypes:
            try:
                doc.links.remove(v)
                found = 1
            except Exception:
                pass
    
    if found:
        doc.save(ignore_permissions=True)