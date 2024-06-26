# Expenses © 2024
# Author:  Ameen Ahmed
# Company: Level Up Marketing & Software Development Services
# Licence: Please refer to LICENSE file


import frappe
from frappe import _
from frappe.utils import cint


# [Hooks]
def before_update_after_submit_event(doc, method=None):
    if doc.is_new() or frappe.flags.get("from_gocardless_update", 0):
        return 0
    
    if doc.has_value_changed("from_gocardless"):
        old = doc.get_doc_before_save()
        if not old:
            doc.load_doc_before_save()
            old = doc.get_doc_before_save()
        if old and cint(old.get("from_gocardless", 0)):
            frappe.throw(_("Gocardless linked bank transaction can't be modified."))
    
    elif cint(doc.get("from_gocardless", 0)):
        for f in [
            "date",
            "status",
            "bank_account",
            "deposit",
            "withdrawal",
            "currency",
            "description",
            "gocardless_transaction_info",
            "reference_number",
            "transaction_id"
        ]:
            if doc.has_value_changed(f):
                frappe.throw(_("Gocardless linked bank transaction can't be modified."))


# [Hooks]
def before_cancel_event(doc, method=None):
    if cint(doc.get("from_gocardless", 0)) and not frappe.flags.get("from_gocardless_update", 0):
        frappe.throw(_("Gocardless linked bank transaction can't be cancelled."))


# [Hooks]
def on_trash_event(doc, method=None):
    if cint(doc.get("from_gocardless", 0)) and not frappe.flags.get("from_gocardless_trash", 0):
        frappe.throw(_("Gocardless linked bank transaction can't be removed."))