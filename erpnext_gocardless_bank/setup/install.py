# ERPNext Gocardless Bank © 2024
# Author:  Ameen Ahmed
# Company: Level Up Marketing & Software Development Services
# Licence: Please refer to LICENSE file


import frappe


# [Hooks]
def before_install():
    from erpnext_gocardless_bank import __production__
    
    if not __production__:
        from .uninstall import after_uninstall
        
        after_uninstall()
    else:
        frappe.clear_cache()


# [Hooks]
def after_sync():
    dt = "Workspace"
    name = "ERPNext Integrations"
    if not frappe.db.exists(dt, name):
        return 0
    
    from .uninstall import (
        clean_workspace,
        get_doctypes
    )
    
    doc = frappe.get_doc(dt, name)
    if doc.links:
        clean_workspace(doc, False)
    
    doctypes = get_doctypes(True)
    for i in range(len(doctypes)):
        v = doctypes.pop(0)
        doc.append("links", {
            "dependencies": "",
            "hidden": 0,
            "is_query_report": 0,
            "label": v,
            "link_count": 0,
            "link_to": v,
            "link_type": "DocType",
            "onboard": 0,
            "type": "Link"
        })
    
    try:
        doc.save(ignore_permissions=True)
    except Exception:
        pass