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
    
    from .datetime import today_utc_date
    
    dt = "Gocardless Bank"
    banks = frappe.get_all(
        dt,
        fields=["name"],
        filters=[
            [dt, "auth_id", "!=", ""],
            [dt, "auth_status", "=", "Linked"],
            [dt, "auth_expiry", "<", today_utc_date()]
        ],
        pluck="name",
        ignore_permissions=True,
        strict=False
    )
    if banks:
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
                }, _("Unable to update Gocardless bank auth status.")
            )
            return 0
        
        try:
            adoc = frappe.qb.DocType(f"{dt} Account")
            (
                frappe.qb.update(adoc)
                .set(adoc.status, "Expired")
                .where(adoc.parent.isin(banks))
                .where(adoc.parenttype == dt)
                .where(adoc.parentfield == "bank_accounts")
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
    from .datetime import today_utc_date
    
    dt = "Gocardless Bank"
    banks = frappe.get_all(
        dt,
        fields=["name"],
        filters=[
            [dt, "disabled", "=", 0],
            [dt, "auto_sync", "=", 1],
            [dt, "auth_id", "!=", ""],
            [dt, "auth_status", "=", "Linked"],
            [dt, "auth_expiry", ">=", today_utc_date()]
        ],
        pluck="name",
        ignore_permissions=True,
        strict=False
    )
    if banks:
        for bank in banks:
            sync_bank(bank, "Auto")


# [Internal]
def sync_bank(name, trigger):
    from frappe.utils import cint
    
    from .bank_transaction import (
        _SYNC_KEY_,
        queue_bank_transactions_sync,
        get_dates_list
    )
    from .cache import (
        get_cached_doc,
        get_cache
    )
    from .datetime import (
        today_utc_date,
        to_date_obj,
        reformat_date
    )
    from .system import settings, get_client
    
    dt = "Gocardless Bank"
    today = today_utc_date()
    today_obj = to_date_obj(today)
    doc = get_cached_doc(dt, name)
    settings = settings()
    client = get_client()
    for v in doc.bank_accounts:
        if v.status != "Ready" or get_cache(_SYNC_KEY_, v.account, True):
            continue
        
        if not v.last_sync:
            dts = [[today, today, 1]]
        else:
            from_dt = reformat_date(v.last_sync)
            from_obj = to_date_obj(from_dt)
            diff = today_obj - from_obj
            diff = cint(diff.days)
            if diff <= 0:
                dts = [[today, today, 1]]
            elif diff == 1:
                dts = [[from_dt, today, 2]]
            else:
                dts = get_dates_list(from_dt, today)
        
        for dt in dts:
            if not queue_bank_transactions_sync(
                settings, client, name, doc.bank, trigger,
                v.name, v.account, v.account_id,
                v.bank_account, dt[0], dt[1], dt[2]
            ):
                _store_error({
                    "error": "An error was raised while syncing bank account.",
                    "bank": name,
                    "trigger": trigger,
                    "from_dt": dt[0],
                    "to_dt": dt[1],
                    "data": v.as_dict(convert_dates_to_str=True)
                })


# [Internal]
def update_bank_accounts_status():
    dt = "Gocardless Bank"
    banks = frappe.get_all(
        dt,
        fields=["name"],
        filters=[
            [dt, "auth_id", "!=", ""],
            [dt, "auth_status", "=", "Linked"]
        ],
        pluck="name",
        ignore_permissions=True,
        strict=False
    )
    if not banks:
        return 0
    
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
            [adt, "parent", "in", banks],
            [adt, "parenttype", "=", dt],
            [adt, "parentfield", "=", "bank_accounts"],
            [adt, "status", "!=", "Ready"]
        ]
    )
    if not accounts:
        return 0
    
    from .bank_account import update_bank_account_data
    from .system import get_client
            
    client = get_client()
    for v in accounts:
        data = client.get_account_data(v["account_id"])
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