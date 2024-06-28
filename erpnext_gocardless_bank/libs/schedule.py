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
    
    from .bank import get_expired_auth_banks
    
    banks = get_expired_auth_banks()
    if banks:
        from .bank import expire_banks_auth
        
        ret = expire_banks_auth(banks)
        if ret and isinstance(ret, str):
            _store_error(
                {
                    "error": "Unable to update bank auth status.",
                    "banks": banks,
                    "exception": ret
                },
                _("Unable to update Gocardless bank auth status.")
            )
            return 0
        
        from .bank_account import expire_banks_bank_accounts
        
        ret = expire_banks_bank_accounts(banks)
        if ret and isinstance(ret, str):
            _store_error(
                {
                    "error": "Unable to update bank accounts status",
                    "banks": banks,
                    "exception": ret
                },
                _("Unable to update Gocardless bank accounts status.")
            )
            return 0
    
    update_bank_accounts_status()


# [Internal]
def sync_banks():
    from .bank import get_auto_sync_banks
    
    banks = get_auto_sync_banks()
    if not banks:
        return 0
    
    from .datetime import today_date
    from .system import settings
    
    settings_doc = frappe._dict(settings().as_dict(
        convert_dates_to_str=True,
        no_child_table_fields=True
    ))
    today = today_date()
    for i in range(len(banks)):
        sync_bank(settings, settings_doc, banks.pop(0), today)


# [Internal]
def sync_bank(settings, settings_doc, name, today):
    from .bank import get_bank_doc
    
    doc = get_bank_doc(name)
    if not doc:
        return 0
    
    from .system import get_client
    
    client = get_client(doc.company, settings)
    if isinstance(client, dict):
        return 0
    
    from .bank_account import AccountStatus
    from .bank_transaction import (
        _SYNC_KEY_,
        can_sync_transactions,
        queue_bank_transactions_sync
    )
    from .cache import get_cache
    from .datetime import (
        date_to_datetime,
        reformat_datetime,
        is_date_gte,
        dates_diff_days,
        add_date
    )
    
    rows = []
    for v in doc.bank_accounts:
        if (
            v.status != AccountStatus.re or
            not v.bank_account_ref or
            get_cache(_SYNC_KEY_, v.account)
        ):
            continue
        
        rows.append(frappe._dict(v.as_dict(
            convert_dates_to_str=True,
            no_child_table_fields=True
        )))
    
    doc = frappe._dict(doc.as_dict(
        convert_dates_to_str=True,
        no_child_table_fields=True
    ))
    today_start = date_to_datetime(today, start=True)
    for i in range(len(rows)):
        row = rows.pop(0)
        if not can_sync_transactions(doc, row, today_start):
            continue
        
        fdt = today
        tdt = None
        if row.last_sync:
            fdt = reformat_datetime(row.last_sync)
            if not fdt:
                fdt = today
            else:
                fdt = fdt.split(" ")[0]
                if not is_date_gte(today, fdt):
                    fdt = today
                elif dates_diff_days(fdt, today) > doc.transaction_days:
                    tdt = add_date(fdt, days=doc.transaction_days, as_string=True)
        
        if fdt != today:
            ddt = 1
        else:
            ddt = dates_diff_days(fdt, tdt or today)
            ddt += 1
        
        queue_bank_transactions_sync(settings_doc, client, doc, row, fdt, tdt, ddt, today, True)


# [Internal]
def update_bank_accounts_status():
    from .bank import get_linked_banks
    
    banks = get_linked_banks()
    if not banks:
        return 0
    
    from .bank_account import get_unready_banks_bank_accounts
    
    accounts = get_unready_banks_bank_accounts(list(banks.keys()))
    if not accounts:
        return 0
    
    from .bank_account import update_bank_account_data
    from .system import (
        settings,
        get_client
    )
    
    settings = settings()
    clients = {}
    updated = {}
    for i in range(len(accounts)):
        v = accounts.pop(0)
        p = v["parent"]
        if p not in banks:
            continue
        
        if p not in clients:
            client = get_client(banks[p]["company"], settings)
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
            updated[p] = banks[p]["bank"]
        except Exception as exc:
            _store_error({
                "error": "Unable to update bank account status",
                "account_data": v,
                "data": data,
                "exception": str(exc)
            })
    
    banks.clear()
    clients.clear()
    if updated:
        from .realtime import emit_reload_bank_accounts
        
        for p in updated:
            emit_reload_bank_accounts({
                "name": p,
                "bank": updated.pop(p)
            })


# [Internal]
def _store_error(data, err=None):
    from .common import store_error
    
    store_error(data)
    if err:
        from .common import log_error
        
        log_error(err)