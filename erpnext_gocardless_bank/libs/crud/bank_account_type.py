# Expenses © 2024
# Author:  Ameen Ahmed
# Company: Level Up Marketing & Software Development Services
# Licence: Please refer to LICENSE file


import frappe
from frappe import _
from frappe.utils import cint


# [Hooks]
def on_trash_event(doc, method=None):
    if cint(doc.from_gocardless) and not frappe.flags.get("from_gocardless_trash", 0):
        frappe.throw(_("Gocardless linked bank account type can't be removed."))