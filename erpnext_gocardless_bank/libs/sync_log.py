# ERPNext Gocardless Bank © 2024
# Author:  Ameen Ahmed
# Company: Level Up Marketing & Software Development Services
# Licence: Please refer to LICENSE file


import frappe


# [Clean, Internal]
_LOG_DT_ = "Gocardless Sync Log"


# [Bank Transaction]
def get_sync_data(bank, account, date):
    dt = _LOG_DT_
    data = frappe.get_all(
        dt,
        fields=["sync_id"],
        filters=[
            [dt, "bank", "=", bank],
            [dt, "bank_account", "=", account],
            [dt, "modified", "between", [
                date + " 00:00:00",
                date + " 23:59:59"
            ]]
        ],
        pluck="sync_id",
        distinct=True,
        ignore_permissions=True,
        strict=False
    )
    if not isinstance(data, list):
        return None
    
    return data


# [Bank Transaction]
def add_sync_data(sync_id, bank, account, trigger, total):
    (frappe.new_doc(_LOG_DT_)
        .update({
            "sync_id": sync_id,
            "bank": bank,
            "bank_account": account,
            "trigger": trigger,
            "total_transactions": total
        })
        .insert(ignore_permissions=True, ignore_mandatory=True))