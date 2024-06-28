# ERPNext Gocardless Bank © 2024
# Author:  Ameen Ahmed
# Company: Level Up Marketing & Software Development Services
# Licence: Please refer to LICENSE file


import frappe


# [Clean, Internal]
_LOG_DT_ = "Gocardless Sync Log"


# [Bank Transaction]
LogTrigger = frappe._dict({
    "a": "Auto",
    "m": "Manual"
})


# [Internal]
LogStatus = frappe._dict({
    "p": "Pending",
    "o": "Ongoing",
    "f": "Finished"
})


# [Bank Transaction]
def get_total_sync_logs(bank, account, today):
    dt = _LOG_DT_
    return frappe.db.count(
        dt,
        [
            [dt, "bank", "=", bank],
            [dt, "account", "=", account],
            [dt, "creation", ">=", today]
        ]
    )


# [Bank Transaction]
def add_sync_data(bank, account, from_dt, to_dt, trigger):
    doc = frappe.new_doc(_LOG_DT_)
    doc.update({
        "bank": bank,
        "account": account,
        "from_date": from_dt,
        "to_date": to_dt,
        "transactions": 0,
        "trigger": trigger,
        "status": LogStatus.p
    })
    doc.insert(ignore_permissions=True, ignore_mandatory=True)
    return doc.name


# [Bank Transaction]
def ongoing_sync_status(name):
    frappe.db.set_value(_LOG_DT_, name, "status", LogStatus.o)


# [Bank Transaction]
def update_sync_total(name, total):
    frappe.db.set_value(_LOG_DT_, name, "transactions", total)


# [Bank Transaction]
def finish_sync_status(name):
    frappe.db.set_value(_LOG_DT_, name, "status", LogStatus.f)