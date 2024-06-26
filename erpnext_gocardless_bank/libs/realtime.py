# ERPNext Gocardless Bank © 2024
# Author:  Ameen Ahmed
# Company: Level Up Marketing & Software Development Services
# Licence: Please refer to LICENSE file


import frappe


# [G Settings]
def emit_status_changed(data=None):
    emit_event("gocardless_status_changed", data)


# [G Bank, Bank, Bank Account]
def emit_bank_error(data=None):
    emit_event("gocardless_bank_error", data)


# [Bank, Schedule]
def emit_reload_bank_accounts(data=None):
    emit_event("gocardless_reload_bank_accounts", data)


# [Internal]
def emit_event(event: str, data):
    frappe.publish_realtime(event=event, message=data)