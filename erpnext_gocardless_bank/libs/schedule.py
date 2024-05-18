# ERPNext Gocardless Bank © 2024
# Author:  Ameen Ahmed
# Company: Level Up Marketing & Software Development Services
# Licence: Please refer to LICENSE file


import frappe


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
            log_error(exc)
            error(_("Unable to update Gocardless bank auth status"), False, "xYRxZTKz99")
        
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
            from .common import store_error, log_error
            
            store_error({
                "error": "Unable to update bank accounts status",
                "banks": banks,
                "exception": str(exc)
            })
            log_error(_("Unable to update Gocardless bank accounts status."))
    
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
    from .bank_transaction import (
        _SYNC_KEY_,
        queue_bank_transactions_sync
    )
    from .cache import (
        get_cached_doc,
        get_cache
    )
    from .datetime import (
        now_utc,
        to_date,
        reformat_date,
        add_date
    )
    from .system import settings, get_client
    
    dt = "Gocardless Bank"
    now = now_utc()
    today = to_date(now)
    doc = get_cached_doc(dt, name)
    settings = settings()
    client = get_client()
    for v in doc.bank_accounts:
        if v.status != "Ready" or get_cache(_SYNC_KEY_, v.account):
            continue
        
        from_dt = None
        to_dt = today
        if v.last_sync:
            from_dt = reformat_date(v.last_sync)
            if from_dt == today:
                from_dt = None
            else:
                from_obj = to_date(from_dt)
                delta = to_date(to_dt) - from_obj
                if cint(delta.days) > 1:
                    to_dt = add_date(from_obj, days=1, as_string=True)
        
        if not from_dt:
            from_dt = add_date(now, days=-1, as_string=True)
        
        if not queue_bank_transactions_sync(
            settings, client, name, doc.bank, trigger,
            v.name, v.account, v.account_id,
            v.bank_account, from_dt, to_dt
        ):
            return 0


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
        pluck="name"
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
    from .common import to_json
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
            from .common import store_error, log_error
            
            store_error({
                "error": "Unable to update account status",
                "data": v,
                "exception": str(exc)
            })
            log_error(_("Unable to update account status of {0} for {1}").format(v["account"], v["parent"]))