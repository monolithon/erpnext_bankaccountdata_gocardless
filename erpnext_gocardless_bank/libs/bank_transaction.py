# ERPNext Gocardless Bank © 2024
# Author:  Ameen Ahmed
# Company: Level Up Marketing & Software Development Services
# Licence: Please refer to LICENSE file


import hashlib
import uuid

import frappe


# [Schedule, Internal]
_SYNC_KEY_ = "gocardless_auto_sync"


# [Internal]
_SYNC_LIMIT = 4


# [G Bank Form, *Bank Account Form]
@frappe.whitelist(methods=["POST"])
def enqueue_bank_transactions_sync(bank, account, from_dt=None, to_dt=None):
    if (
        not bank or not isinstance(bank, str) or
        not account or not isinstance(account, str) or
        (from_dt and not isinstance(from_dt, str)) or
        (to_dt and not isinstance(to_dt, str))
    ):
        return {"error": _("Arguments are invalid.")}
    
    from .system import settings
    
    settings = settings()
    if not settings.is_enabled:
        from .system import app_disabled_message
        
        return {"error": app_disabled_message(), "disabled": 1}
    
    from .cache import get_cache
    
    if get_cache(_SYNC_KEY_, account, True):
        return {"info": _("Bank account sync is in progress.")}
    
    from .cache import get_cached_doc
    
    dt = "Gocardless Bank"
    doc = get_cached_doc(dt, bank)
    if not doc:
        return {"error": _("Gocardless bank \"{0}\" doesn't exist.").format(bank)}
    
    accounts = {v.account:v for v in doc.bank_accounts}
    if account not in accounts:
        return {"error": _("Bank account \"{0}\" is not part of Gocardless bank \"{1}\".").format(account, bank)}
    
    from .system import get_client
    
    client = get_client(doc.company, settings)
    if isinstance(client, dict):
        client["disabled"] = 1
        return client
    
    from .datetime import (
        now_utc,
        to_date,
        add_date
    )
    
    now = now_utc()
    today = to_date(now)
    data = accounts[account]
    if from_dt or to_dt:
        from .datetime import reformat_date
        
        if from_dt:
            from_dt = reformat_date(from_dt)
        if to_dt:
            to_dt = reformat_date(to_dt)
        
        if not from_dt and to_dt:
            from_dt = add_date(to_dt, days=-1, as_string=True)
        elif not to_dt and from_dt:
            to_dt = add_date(from_dt, days=1, as_string=True)
        
        if from_dt == today:
            from_dt = None
        else:
            has_error = 0
            if cint(doc.transaction_days):
                diff = now - to_date(from_dt)
                diff = cint(diff.days) - cint(doc.transaction_days)
                if diff > 0:
                    from_dt = add_date(from_dt, days=diff, as_string=True)
            
            for dt in get_dates_list(from_dt, to_dt):
                if not queue_bank_transactions_sync(
                    settings, client, bank, doc.bank, "Manual",
                    data.name, data.account, data.account_id,
                    data.account_currency, data.bank_account, dt[0], dt[1]
                ):
                    has_error += 1
            
            if has_error:
                return {
                    "error": _("An error was raised while syncing bank account \"{0}\" of Gocardless bank \"{1}\".")
                        .format(data.account, bank)
                }
            
            return 1
    
    if not from_dt:
        to_dt = add_date(now, days=1, as_string=True)
        if not queue_bank_transactions_sync(
            settings, client, bank, doc.bank, "Manual",
            data.name, data.account, data.account_id,
            data.account_currency, data.bank_account, today, to_dt
        ):
            return {
                "error": _("An error was raised while syncing bank account \"{0}\" of Gocardless bank \"{1}\".")
                    .format(data.account, bank)
            }
    
    return 1


# [Internal]
def get_dates_list(from_dt, to_dt):
    from .datetime import to_date, add_date
    
    from_obj = to_date(from_dt)
    delta = to_date(to_dt) - from_obj
    diff = cint(delta.days)
    last_date = from_obj
    ret = []
    for i in range(0, diff, 2):
        total += 1
        if i > 0:
            last_date = add_date(last_date, days=1)
        
        fdt = to_date(last_date)
        last_date = add_date(last_date, days=1)
        tdt = to_date(last_date)
        ret.append([fdt, tdt])
    
    return ret


# [Schedule, Internal]
def queue_bank_transactions_sync(
    settings, client, bank, account_bank, trigger, account_name,
    account, account_id, account_currency, bank_account, from_dt, to_dt
):
    from .common import store_info
    from .datetime import today_utc_date
    from .sync_log import get_sync_data
    
    today = today_utc_date()
    sync_data = get_sync_data(bank, account, today)
    if sync_data is None:
        store_info((
            "The sync log data of the bank account {0} that belongs to {1} is invalid."
        ).format(account, account_bank))
        return 0
    
    if len(sync_data) >= _SYNC_LIMIT:
        store_info((
            "The synchronization for the bank account {0} "
            + "of {1} has exceeded the allowed limit {2}."
        ).format(account, account_bank, _SYNC_LIMIT))
        return 0
    
    store_info((
        "The sync transactions for the bank account {0} of {1} has been queued."
    ).format(account, account_bank))
    
    from .background import is_job_running
    
    job_id = f"gocardless-bank-transactions-sync-{account}"
    if not is_job_running(job_id):
        from .background import enqueue_job
        
        enqueue_job(
            "erpnext_gocardless_bank.libs.bank_transaction.sync_bank_transactions",
            job_id,
            queue="long",
            timeout=5000,
            settings=settings,
            client=client,
            sync_id=uuid.uuid4(),
            bank=bank,
            account_bank=account_bank,
            trigger=trigger,
            account_name=account_name,
            account=account,
            account_id=account_id,
            account_currency=account_currency,
            bank_account=bank_account,
            from_dt=from_dt,
            to_dt=to_dt
        )
    
    return 1


# [Internal]
def sync_bank_transactions(
    settings, client, sync_id, bank, account_bank, trigger, account_name,
    account, account_id, account_currency, bank_account, from_dt, to_dt
):
    transactions = client.get_account_transactions(account_id, from_dt, to_dt)
    if transactions and "error" in transactions:
        from .cache import del_cache
        
        del_cache(_SYNC_KEY_, account)
        return 0
    
    from .cache import set_cache
    from .common import store_info
    
    set_cache(_SYNC_KEY_, account, True, 1500)
    result = _dict({
        "entries": [],
        "synced": False,
    })
    
    try:
        if transactions:
            for k in ["booked", "pending"]:
                if (
                    k in transactions and transactions[k] and
                    isinstance(transactions[k], list)
                ):
                    store_info({
                        "info": "Processing bank transactions.",
                        "key": k,
                        "account": account,
                        "data": transactions[k]
                    })
                    
                    add_transactions(
                        result, settings, sync_id, bank, account_bank,
                        trigger, account, account_currency, bank_account, k,
                        client.prepare_entries(transactions.pop(k))
                    )
                else:
                    store_info({
                        "info": "Skipping bank transactions.",
                        "key": k,
                        "account": account
                    })
    finally:
        from .cache import del_cache, clear_doc_cache
        from .sync_log import add_sync_data
        
        if result.synced:
            from .bank_account import update_bank_account_data
            from .datetime import date_to_datetime
            
            last_sync = date_to_datetime(to_dt)
            values = {"last_sync": last_sync}
            
            balances = client.get_account_balances(account_id)
            if balances and "error" not in balances:
                from .common import to_json
                
                values["balances"] = to_json(balances)
            
            update_bank_account_data(account_name, values)
        
        add_sync_data(sync_id, bank, account, trigger, len(result.entries))
        del_cache(_SYNC_KEY_, account)
        clear_doc_cache("Bank Transaction")


# [Internal]
def add_transactions(
    result, settings, sync_id, bank, account_bank, trigger,
    account, account_currency, bank_account, status, transactions
):
    result.synced = True
    for i in range(len(transactions)):
        new_bank_transaction(
            result, settings, account_bank, account, account_currency,
            bank_account, transactions.pop(0), status
        )


# [Internal]
def new_bank_transaction(
    result, settings, account_bank, account,
    account_currency, bank_account, data, status
):
    from .common import store_info, to_json
    from .currency import (
        get_currency_status,
        add_currencies,
        enable_currencies
    )
    from .datetime import today_utc_datetime
    
    if "transaction_id" not in data:
        if settings.bank_transaction_without_id == "Ignore":
            store_info(_(
                "The new {0} transaction for bank account \"{1}\" has been ignored " +
                "since it has no transaction id."
            ).format(status, account))
            store_info(data)
            return 0
        else:
            data["transaction_id"] = uuid.UUID(hashlib.sha256(
                to_json(data, "").encode("utf-8")
            ).hexdigest()[::2])
    
    if "date" not in data:
        if settings.bank_transaction_without_date == "Ignore":
            store_info(_(
                "The new {0} transaction for bank account \"{1}\" has been ignored "
                + "since it has no date."
            ).format(status, account))
            store_info(data)
            return 0
        
        data["date"] = today_utc_datetime()
    
    if "amount" not in data:
        if settings.bank_transaction_without_amount == "Ignore":
            store_info(_(
                "The new {0} transaction for bank account \"{1}\" has been ignored "
                + "since it has no amount."
            ).format(status, account))
            store_info(data)
            return 0
        
        data["amount"] = 0
    
    if "currency" not in data:
        if settings.bank_transaction_without_currency == "Ignore":
            store_info(_(
                "The new {0} transaction for bank account \"{1}\" has been ignored "
                + "since it has no currency."
            ).format(status, account))
            store_info(data)
            return 0
        
        data["currency"] = account_currency
    
    else:
        currency_status = get_currency_status(data["currency"])
        if currency_status is None:
            if settings.bank_transaction_currency_doesnt_exist == "Ignore":
                store_info(_(
                    "The new {0} transaction for bank account \"{1}\" has been ignored " +
                    "since it has no existing currency."
                ).format(status, account))
                store_info(data)
                return 0
            
            add_currencies([data["currency"]])
        elif not currency_status:
            if settings.bank_transaction_currency_disabled == "Ignore":
                return 0
            
            enable_currencies([data["currency"]])
    
    data["amount"] = flt(data["amount"])
    if data["amount"] >= 0:
        debit = abs(data["amount"])
        credit = 0
    else:
        debit = 0
        credit = abs(data["amount"])
    
    status = "Pending" if status == "pending" else "Settled"
    dt = "Bank Transaction"
    
    if not frappe.db.exists(dt, {"transaction_id": data["transaction_id"]}):
        try:
            entry_data = _dict({
                "date": reformat_date(data["date"]),
                "status": status,
                "bank_account": bank_account,
                "deposit": debit,
                "withdrawal": credit,
                "currency": data["currency"],
                "description": data.get("description", ""),
                "gocardless_transaction_info": data.get("information", ""),
                "reference_number": data.get("reference_number", ""),
                "transaction_id": data["transaction_id"],
            })
            
            handle_transaction_supplier(settings, entry_data, account_bank, data)
            handle_transaction_customer(settings, entry_data, account_bank, data)
            
            doc = (frappe.new_doc(dt)
                .update(entry_data)
                .insert(ignore_permissions=True, ignore_mandatory=True)
                .submit())
            
            result.entries.append(doc.name)
        except Exception as exc:
            _store_error({
                "error": "Unable to add new transaction.",
                "account_bank": account_bank,
                "account": account,
                "account_currency": account_currency,
                "bank_account": bank_account,
                "status": status,
                "data": data,
                "exception": str(exc)
            })


# [Internal]
def handle_transaction_supplier(settings, entry, account_bank, data):
    if (
        settings.supplier_exist_in_transaction == "Ignore" or
        "supplier" not in data or
        not data["supplier"] or
        "name" not in data["supplier"]
    ):
        return 0
    
    dt = "Supplier"
    name = data["supplier"]["name"]
    ignore_supplier = False
    if not frappe.db.exists(dt, {"supplier_name": name}):
        if (
            settings.supplier_in_transaction_doesnt_exist == "Ignore" or
            not settings.supplier_default_group
        ):
            return 0
        
        from .cache import clear_doc_cache
        
        try:
            doc = (frappe.new_doc(dt)
                .update({
                    "supplier_name": name,
                    "supplier_group": settings.supplier_default_group,
                    "supplier_type": "Individual",
                })
                .insert(ignore_permissions=True, ignore_mandatory=True))
            entry.party_type = dt
            entry.party = doc.name
            
            clear_doc_cache(dt)
        except Exception as exc:
            _store_error({
                "error": "Unable to create new supplier.",
                "data": data["supplier"],
                "exception": str(exc)
            })
            ignore_supplier = True
    
    else:
        entry.party_type = dt
        entry.party = frappe.db.get_value(dt, {"supplier_name": name}, "name")
        if isinstance(entry.party, list):
            entry.party = entry.party.pop()
    
    if (
        ignore_supplier or
        settings.supplier_bank_account_exist_in_transaction == "Ignore" or
         "account" not in data["supplier"] or
         not data["supplier"]["account"]
    ):
        return 0
    
    from .bank_account import add_party_bank_account
    
    acc_name = add_party_bank_account(name, dt, account_bank, data["supplier"]["account"])
    if not acc_name or not entry.party:
        return 0
    
    from .cache import clear_doc_cache
    
    frappe.db.set_value(
        dt,
        entry.party,
        "default_bank_account",
        acc_name
    )
    clear_doc_cache(dt)


# [Internal]
def handle_transaction_customer(settings, entry, account_bank, data):
    if (
        settings.customer_exist_in_transaction == "Ignore" or
        entry.party_type or
        entry.party or
        "customer" not in data or
        not data["customer"] or
        "name" not in data["customer"]
    ):
        return 0
    
    dt = "Customer"
    name = data["customer"]["name"]
    ignore_customer = False
    if not frappe.db.exists(dt, {"customer_name": name}):
        if (
            settings.customer_in_transaction_doesnt_exist == "Ignore" or
            not settings.customer_default_group or
            not settings.customer_default_territory
        ):
            return 0
        
        from .cache import clear_doc_cache
        
        try:
            doc = (frappe.new_doc(dt)
                .update({
                    "customer_name": name,
                    "customer_type": "Individual",
                    "customer_group": settings.customer_default_group,
                    "territory": settings.customer_default_territory,
                })
                .insert(ignore_permissions=True, ignore_mandatory=True))
            entry.party_type = dt
            entry.party = doc.name
            
            clear_doc_cache(dt)
        except Exception as exc:
            _store_error({
                "error": "Unable to create new customer.",
                "data": data["customer"],
                "exception": str(exc)
            })
            ignore_supplier = True
    else:
        entry.party_type = dt
        entry.party = frappe.db.get_value(dt, {"customer_name": name}, "name")
        if isinstance(entry.party, list):
            entry.party = entry.party.pop()
    
    if (
        ignore_customer or
        settings.customer_bank_account_exist_in_transaction == "Ignore" or
         "account" not in data["customer"] or
         not data["customer"]["account"]
    ):
        return 0
    
    from .bank_account import add_party_bank_account
    
    acc_name = add_party_bank_account(name, dt, account_bank, data["customer"]["account"])
    if not acc_name or not entry.party:
        return 0
    
    from .cache import clear_doc_cache
    
    frappe.db.set_value(
        dt,
        entry.party,
        "default_bank_account",
        acc_name
    )
    clear_doc_cache(dt)


# [Internal]
def _store_error(data):
    from .common import store_error
    
    store_error(data)