# ERPNext Gocardless Bank © 2024
# Author:  Ameen Ahmed
# Company: Level Up Marketing & Software Development Services
# Licence: Please refer to LICENSE file


import frappe
from frappe import _


# [Hooks]
def auto_sync():
    from .system import is_enabled
    
    if is_enabled():
        sync_banks()


# [Hooks]
def update_banks_status():
    from .system import is_enabled
    
    if not is_enabled():
        return 0
    
    from .datetime import today_date
    
    dt = "Gocardless Bank"
    banks = frappe.get_all(
        dt,
        fields=["name"],
        filters=[
            [dt, "auth_id", "!=", ""],
            [dt, "auth_status", "=", "Linked"],
            [dt, "auth_expiry", "<", today_date()]
        ],
        pluck="name",
        ignore_permissions=True,
        strict=False
    )
    if banks and isinstance(banks, list):
        try:
            doc = frappe.qb.DocType(dt)
            (
                frappe.qb.update(doc)
                .set(doc.auth_id, "")
                .set(doc.auth_expiry, "")
                .set(doc.auth_status, "Unlinked")
                .where(doc.name.isin(banks))
            ).run()
        except Exception as exc:
            _store_error(
                {
                    "error": "Unable to update bank auth status.",
                    "banks": banks,
                    "exception": str(exc)
                },
                _("Unable to update Gocardless bank auth status.")
            )
            return 0
        
        try:
            adoc = frappe.qb.DocType(f"{dt} Account")
            (
                frappe.qb.update(adoc)
                .set(adoc.status, "Expired")
                .where(adoc.parenttype == dt)
                .where(adoc.parentfield == "bank_accounts")
                .where(adoc.parent.isin(banks))
            ).run()
        except Exception as exc:
            _store_error(
                {
                    "error": "Unable to update bank accounts status",
                    "banks": banks,
                    "exception": str(exc)
                },
                _("Unable to update Gocardless bank accounts status.")
            )
            return 0
    
    update_bank_accounts_status()


# [Internal]
def sync_banks():
    from .datetime import today_date
    
    dt = "Gocardless Bank"
    banks = frappe.get_all(
        dt,
        fields=["name"],
        filters=[
            [dt, "disabled", "=", 0],
            [dt, "auto_sync", "=", 1],
            [dt, "auth_id", "!=", ""],
            [dt, "auth_status", "=", "Linked"],
            [dt, "auth_expiry", ">=", today_date()]
        ],
        pluck="name",
        ignore_permissions=True,
        strict=False
    )
    if not banks or not isinstance(banks, list):
        return 0
    
    from .datetime import today_date
    from .system import settings
    
    settings = settings()
    today = today_date()
    for i in range(len(banks)):
        sync_bank(settings, banks.pop(0), today, "Auto")


# [Internal]
def sync_bank(settings, name, today, trigger):
    # from frappe.utils import cint
    
    from .bank import get_bank_doc
    from .bank_transaction import (
        _SYNC_KEY_,
        queue_bank_transactions_sync,
        get_dates_list
    )
    from .cache import get_cache
    from .datetime import (
        reformat_datetime,
        is_date_gt
    )
    from .system import get_client
    
    doc = get_bank_doc(name)
    # trans_days = cint(doc.transaction_days)
    client = get_client(doc.company, settings)
    if isinstance(client, dict):
        return 0
    
    for v in doc.bank_accounts:
        if v.status != "Ready" or get_cache(_SYNC_KEY_, v.account, True):
            continue
        
        fdt = today
        tdt = today
        if v.last_sync:
            fdt = reformat_datetime(v.last_sync)
            fdt = fdt.split(" ")[0]
            if not is_date_gt(today, fdt):
                fdt = today
            # elif trans_days > 0:
            #     from .datetime import dates_diff_days
                
            #     dif = dates_diff_days(fdt, tdt)
            #     if dif > trans_days:
            #         from .datetime import add_date
                    
            #         dif = dif - trans_days
            #         fdt = add_date(fdt, days=dif, as_string=True)
        
        err_dates = []
        dates = get_dates_list(fdt, tdt)
        for i in range(len(dates)):
            dt = dates.pop(0)
            if not queue_bank_transactions_sync(
                settings, client, doc.name, doc.bank, trigger,
                v.name, v.account, v.account_id, v.account_currency,
                v.bank_account_ref, dt[0], dt[1], dt[2]
            ):
                err_dates.append([dt[0], dt[1]])
        
        if err_dates:
            _store_error({
                "error": "Error was raised in schedule while syncing bank account.",
                "bank": doc.name,
                "account": v.account,
                "trigger": trigger,
                "dates": err_dates,
                "data": v.as_dict(convert_dates_to_str=True)
            })


# [Internal]
def update_bank_accounts_status():
    dt = "Gocardless Bank"
    banks = frappe.get_all(
        dt,
        fields=["name", "company"],
        filters=[
            [dt, "auth_id", "!=", ""],
            [dt, "auth_status", "=", "Linked"]
        ],
        ignore_permissions=True,
        strict=False
    )
    if not banks or not isinstance(banks, list):
        return 0
    
    banks = {v["name"]:v["company"] for v in banks}
    
    adt = f"{dt} Account"
    accounts = frappe.get_all(
        adt,
        fields=[
            "parent",
            "name",
            "account",
            "account_id",
            "status"
        ],
        filters=[
            [adt, "parent", "in", list(banks.keys())],
            [adt, "parenttype", "=", dt],
            [adt, "parentfield", "=", "bank_accounts"],
            [adt, "status", "!=", "Ready"]
        ]
    )
    if not accounts or not isinstance(accounts, list):
        return 0
    
    from .bank_account import update_bank_account_data
    from .system import (
        settings,
        get_client
    )
    
    settings = settings()
    clients = {}
    for v in accounts:
        p = v["parent"]
        if p not in banks:
            continue
        
        if p not in clients:
            client = get_client(banks[p], settings)
            if isinstance(client, dict):
                continue
            
            clients[p] = client
        
        data = clients[p].get_account_data(v["account_id"])
        if not data or "error" in data:
            continue
        
        if data["status"] == v["status"]:
            continue
        
        try:
            update_bank_account_data(v["name"], {"status": data["status"]})
        except Exception as exc:
            _store_error({
                "error": "Unable to update bank account status",
                "account_data": v,
                "data": data,
                "exception": str(exc)
            })


# [Internal]
def _store_error(data, err=None):
    from .common import store_error
    
    store_error(data)
    if err:
        from .common import log_error
        
        log_error(err)