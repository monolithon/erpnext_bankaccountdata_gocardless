# ERPNext Nordigen © 2023
# Author:  Ameen Ahmed
# Company: Level Up Marketing & Software Development Services
# Licence: Please refer to LICENSE file


import frappe
from frappe import _
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

from erpnext_nordigen.libs.nordigen import clear_sync_cache


def after_install():
    clear_sync_cache()
    _create_custom_fields()
    _add_link_to_workspace()


def _create_custom_fields():
    create_custom_fields({
        "Bank Transaction": [
            {
                "label": _("Nordigen Information"),
                "fieldname": "nordigen_transaction_info",
                "fieldtype": "Long Text",
                "no_copy": 1,
                "read_only": 1,
                "insert_after": "description",
            }
        ],
        "Bank Account": [
            {
                "label": _("Bank Account No"),
                "fieldname": "nordigen_bank_account_no",
                "fieldtype": "Data",
                "hidden": 1,
                "no_copy": 1,
                "read_only": 1,
                "insert_after": "bank_account_no",
            }
        ]
    })


def _add_link_to_workspace():
    dt = "Workspace"
    name = "ERPNext Integrations"
    if not frappe.db.exists(dt, name):
        return 0
        
    doc = frappe.get_doc(dt, name)
    keys = ["Nordigen Settings", "Nordigen Bank", "Nordigen Sync Log"]
    
    for v in doc.links:
        if v.type == "Link" and v.label in keys:
            try:
                doc.links.remove(v)
            except Exception:
                pass
    
    for key in keys:
        doc.append("links", {
            "dependencies": "",
            "hidden": 0,
            "is_query_report": 0,
            "label": key,
            "link_count": 0,
            "link_to": key,
            "link_type": "DocType",
            "onboard": 0,
            "type": "Link"
        })
    
    doc.save(ignore_permissions=True)