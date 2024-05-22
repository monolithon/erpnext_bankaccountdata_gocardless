# ERPNext Gocardless Bank © 2024
# Author:  Ameen Ahmed
# Company: Level Up Marketing & Software Development Services
# Licence: Please refer to LICENSE file


import frappe


# [Hooks, Install]
def after_uninstall():
    dt = "Workspace"
    name = "ERPNext Integrations"
    if frappe.db.exists(dt, name):
        doc = frappe.get_doc(dt, name)
        if doc.links:
            clean_workspace(doc)
    
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
        ["DocType", get_doctypes()],
        ["Module Def", ["ERPNext Gocardless Bank"]]
    ]
    for i in range(len(docs)):
        doc = docs.pop(0)
        for x in range(len(doc[1])):
            try:
                frappe.delete_doc(
                    doc[0], doc[1].pop(0),
                    ignore_permissions=True,
                    ignore_missing=True,
                    ignore_on_trash=True,
                    delete_permanently=True
                )
            except Exception:
                pass
    
    frappe.clear_cache()


# [Install, Internal]
def get_doctypes(for_links=False):
    docs = [
        "Gocardless Bank Account",
        "Gocardless Access",
        "Gocardless Sync Log",
        "Gocardless Bank",
        "Gocardless Settings"
    ]
    if for_links:
        docs = docs[2:]
        docs.reverse()
    
    return docs


# [Install, Internal]
def clean_workspace(doc, save=True):
    doctypes = get_doctypes()
    links = []
    for v in doc.links:
        if v.link_to and v.link_to in doctypes:
            links.append(v)
    
    doctypes.clear()
    if not links:
        return 0
    
    for i in range(len(links)):
        doc.links.remove(links.pop(0))
    
    if not save:
        return 0
    
    try:
        doc.save(ignore_permissions=True)
    except Exception:
        pass
    