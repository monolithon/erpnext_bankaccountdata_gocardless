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
    from .uninstall import get_doctypes
    
    dt = "Workspace"
    name = "ERPNext Integrations"
    if not frappe.db.exists(dt, name):
        return 0
    
    doctypes = get_doctypes()[2:]
    doctypes.reverse()
    doc = frappe.get_doc(dt, name)
    for v in doc.links:
        if (
            v.type == "Link" and (
                v.link_to in doctypes or
                (
                    v.link_to == "Mpesa Settings" and
                    not frappe.db.exists("DocType", v.link_to)
                )
            )
        ):
            try:
                doc.links.remove(v)
            except Exception:
                pass
    
    for v in doctypes:
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
    
    doc.save(ignore_permissions=True)