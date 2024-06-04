# ERPNext Gocardless Bank © 2024
# Author:  Ameen Ahmed
# Company: Level Up Marketing & Software Development Services
# Licence: Please refer to LICENSE file


import frappe
from frappe import _


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
        return {"error": _("Arguments required for bank transactions sync are invalid.")}
    
    from .system import settings
    
    settings = settings()
    if not settings.is_enabled:
        from .system import app_disabled_message
        
        return {"error": app_disabled_message(), "disabled": 1}
    
    from .cache import get_cache
    
    if get_cache(_SYNC_KEY_, account, True):
        return {"info": _("Bank transactions sync is in progress.")}
    
    from .bank import get_bank_doc
    
    doc = get_bank_doc(bank)
    if not doc:
        return {"error": _("Gocardless bank \"{0}\" doesn't exist.").format(bank)}
    
    data = None
    for v in doc.bank_accounts:
        if v.account == account:
            data = v
            break
    
    if not data:
        return {"error": _("Bank account \"{0}\" doesn't belong to Gocardless bank \"{1}\".").format(account, bank)}
    
    from .system import get_client
    
    client = get_client(doc.company, settings)
    if isinstance(client, dict):
        client["disabled"] = 1
        return client
    
    from .datetime import today_utc_date
    
    today = today_utc_date()
    _store_info({
        "info": "Before preparing from & to dates",
        "bank": doc.name,
        "account": data.account,
        "from": from_dt,
        "to": to_dt,
        "data": data.as_dict(convert_dates_to_str=True)
    })
    if from_dt:
        from frappe.utils import cint
        
        from .datetime import (
            reformat_date,
            to_date_obj
        )
        
        today_obj = to_date_obj(today)
        from_dt = reformat_date(from_dt)
        from_obj = to_date_obj(from_dt)
        from_diff = today_obj - from_obj
        from_diff = cint(from_diff.days)
        if from_diff <= 0:
            from_dt = None
        else:
            trans_days = cint(doc.transaction_days)
            if trans_days and trans_days < from_diff:
                from .datetime import add_date
                
                diff = from_diff - trans_days
                from_dt = add_date(from_dt, days=diff, as_string=True)
                from_obj = to_date_obj(from_dt)
            
            if not to_dt:
                to_dt = from_dt
            else:
                to_dt = reformat_date(to_dt)
                if to_dt != from_dt:
                    to_obj = to_date_obj(to_dt)
                    diff = to_obj - today_obj
                    diff = cint(diff.days)
                    if diff > 0:
                        to_dt = today
                    else:
                        diff = to_obj - from_obj
                        diff = cint(diff.days)
                        if diff < 0:
                            to_dt = from_dt
    
    if not from_dt:
        from_dt = today
        to_dt = today
    
    if from_dt == to_dt:
        _store_info({
            "info": "After preparing from & to dates",
            "bank": doc.name,
            "account": data.account,
            "from": from_dt,
            "to": to_dt,
            "data": data.as_dict(convert_dates_to_str=True)
        })
        if not queue_bank_transactions_sync(
            settings, client, doc.name, doc.bank, "Manual",
            data.name, data.account, data.account_id,
            data.account_currency, data.bank_account_ref,
            from_dt, to_dt, 1
        ):
            return {
                "error": _("An error was raised while syncing bank account \"{0}\" of Gocardless bank \"{1}\".")
                    .format(data.account, doc.name)
            }
    else:
        has_error = 0
        dts = get_dates_list(from_dt, to_dt)
        _store_info({
            "info": "After preparing from & to dates",
            "bank": doc.name,
            "account": data.account,
            "dates": dts,
            "data": data.as_dict(convert_dates_to_str=True)
        })
        for dt in dts:
            if not queue_bank_transactions_sync(
                settings, client, doc.name, doc.bank, "Manual",
                data.name, data.account, data.account_id,
                data.account_currency, data.bank_account_ref,
                dt[0], dt[1], dt[2]
            ):
                has_error += 1
        
        if has_error:
            return {
                "error": _("An error was raised while syncing bank account \"{0}\" of Gocardless bank \"{1}\".")
                    .format(data.account, doc.name)
            }
    
    return 1


# [Internal]
def get_dates_list(from_dt, to_dt):
    from frappe.utils import cint
    
    from .datetime import (
        to_date,
        to_date_obj,
        add_date
    )
    
    from_obj = to_date_obj(from_dt)
    to_obj = to_date_obj(to_dt)
    delta = to_obj - from_obj
    diff = cint(delta.days)
    if diff == 1:
        return [[from_dt, to_dt, 2]]
    
    last_date = from_obj
    ret = []
    for i in range(diff):
        fdt = to_date(last_date)
        last_date = add_date(last_date, days=1)
        if last_date > to_obj:
            ret.append([fdt, fdt, 1])
            break
        
        tdt = to_date(last_date)
        ret.append([fdt, tdt, 2])
        last_date = add_date(last_date, days=1)
        if last_date > to_obj:
            break
    
    return ret


# [Schedule, Internal]
def queue_bank_transactions_sync(
    settings, client, bank, account_bank, trigger, account_name,
    account, account_id, account_currency, bank_account_ref,
    from_dt, to_dt, dt_diff=1
):
    from .datetime import today_utc_date
    from .sync_log import get_sync_data
    
    today = today_utc_date()
    sync_data = get_sync_data(bank, account, today)
    if sync_data is None:
        _store_info({
            "error": "Sync log data is invalid.",
            "bank": bank,
            "account_bank": account_bank,
            "account": account
        })
        return 0
    
    if len(sync_data) >= _SYNC_LIMIT:
        _store_info({
            "error": "Sync exceeded the allowed limit.",
            "bank": bank,
            "account_bank": account_bank,
            "account": account,
            "limit": _SYNC_LIMIT
        })
        return 0
    
    from .background import is_job_running
    
    job_id = f"gocardless-bank-transactions-sync-{account}"
    if not is_job_running(job_id):
        from .common import unique_key
        from .background import enqueue_job
        
        enqueue_job(
            "erpnext_gocardless_bank.libs.bank_transaction.sync_bank_transactions",
            job_id,
            queue="long",
            timeout=10000 * dt_diff,
            settings=settings,
            client=client,
            sync_id=unique_key(),
            bank=bank,
            account_bank=account_bank,
            trigger=trigger,
            account_name=account_name,
            account=account,
            account_id=account_id,
            account_currency=account_currency,
            bank_account_ref=bank_account_ref,
            from_dt=from_dt,
            to_dt=to_dt
        )
    
    return 1


# [Internal]
def sync_bank_transactions(
    settings, client, sync_id, bank, account_bank, trigger, account_name,
    account, account_id, account_currency, bank_account_ref, from_dt, to_dt
):
    transactions = client.get_account_transactions(account_id, from_dt, to_dt)
    if transactions and "error" in transactions:
        from .cache import del_cache
        
        del_cache(_SYNC_KEY_, account)
        return 0
    
    from .cache import set_cache
    
    set_cache(_SYNC_KEY_, account, True, 1500)
    result = frappe._dict({
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
                    _store_info({
                        "info": "Processing bank transactions.",
                        "key": k,
                        "account": account,
                        "data": transactions[k]
                    })
                    
                    add_transactions(
                        result, settings, sync_id, bank, account_bank,
                        trigger, account, account_currency, bank_account_ref, k,
                        client.prepare_entries(transactions.pop(k))
                    )
                else:
                    _store_info({
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
    account, account_currency, bank_account_ref, status, transactions
):
    result.synced = True
    for i in range(len(transactions)):
        new_bank_transaction(
            result, settings, account_bank, account, account_currency,
            bank_account_ref, transactions.pop(0), status
        )


# [Internal]
def new_bank_transaction(
    result, settings, account_bank, account,
    account_currency, bank_account_ref, data, status
):
    from .datetime import today_utc_datetime
    
    if "transaction_id" not in data:
        if settings.bank_transaction_without_id == "Ignore":
            _store_info({
                "error": "Transaction has no id so ignored.",
                "account_bank": account_bank,
                "account": account,
                "account_currency": account_currency,
                "bank_account_ref": bank_account_ref,
                "status": status,
                "data": data
            })
            return 0
        else:
            from .common import unique_key
            
            data["transaction_id"] = unique_key(data)
    
    if "date" not in data:
        if settings.bank_transaction_without_date == "Ignore":
            _store_info({
                "error": "Transaction has no date so ignored.",
                "account_bank": account_bank,
                "account": account,
                "account_currency": account_currency,
                "bank_account_ref": bank_account_ref,
                "status": status,
                "data": data
            })
            return 0
        
        data["date"] = today_utc_datetime()
    
    if "amount" not in data:
        if settings.bank_transaction_without_amount == "Ignore":
            _store_info({
                "error": "Transaction has no amount so ignored.",
                "account_bank": account_bank,
                "account": account,
                "account_currency": account_currency,
                "bank_account_ref": bank_account_ref,
                "status": status,
                "data": data
            })
            return 0
        
        data["amount"] = 0
    
    if "currency" not in data:
        if settings.bank_transaction_without_currency == "Ignore":
            _store_info({
                "error": "Transaction has no currency so ignored.",
                "account_bank": account_bank,
                "account": account,
                "account_currency": account_currency,
                "bank_account_ref": bank_account_ref,
                "status": status,
                "data": data
            })
            return 0
        
        data["currency"] = account_currency
    
    else:
        from .currency import get_currency_status
        
        currency_status = get_currency_status(data["currency"])
        if currency_status is None:
            if settings.bank_transaction_currency_doesnt_exist == "Ignore":
                _store_info({
                    "error": "Transaction currency doesn't exist so ignored.",
                    "account_bank": account_bank,
                    "account": account,
                    "account_currency": account_currency,
                    "bank_account_ref": bank_account_ref,
                    "status": status,
                    "data": data
                })
                return 0
            
            from .currency import add_currencies
            
            add_currencies([data["currency"]])
        elif not currency_status:
            if settings.bank_transaction_currency_disabled == "Ignore":
                _store_info({
                    "error": "Transaction currency is disabled so ignored.",
                    "account_bank": account_bank,
                    "account": account,
                    "account_currency": account_currency,
                    "bank_account_ref": bank_account_ref,
                    "status": status,
                    "data": data
                })
                return 0
            
            from .currency import enable_currencies
            
            enable_currencies([data["currency"]])
    
    from frappe.utils import flt
    
    data["amount"] = flt(data["amount"])
    def_amount = 0.0
    if data["amount"] >= def_amount:
        debit = abs(data["amount"])
        credit = def_amount
    else:
        debit = def_amount
        credit = abs(data["amount"])
    
    dt = "Bank Transaction"
    status = "Pending" if status == "pending" else "Settled"
    if not frappe.db.exists(dt, {"transaction_id": data["transaction_id"]}):
        from .datetime import reformat_date
        
        try:
            entry_data = frappe._dict({
                "date": reformat_date(data["date"]),
                "status": status,
                "bank_account": bank_account_ref,
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
                "bank_account_ref": bank_account_ref,
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
            ignore_customer = True
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


# [Internal]
def _store_info(data):
    from .common import store_info
    
    store_info(data)