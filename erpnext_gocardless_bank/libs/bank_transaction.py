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
    if not settings._is_enabled:
        from .system import app_disabled_message
        
        return {"error": app_disabled_message(), "disabled": 1}
    
    from .bank import get_bank_doc
    
    doc = get_bank_doc(bank)
    if not doc:
        return {"error": _("Bank \"{0}\" doesn't exist.").format(bank)}
    
    if doc._is_draft:
        return {"error": _("Bank \"{0}\" hasn't been submitted.").format(doc.name)}
    
    if doc._is_cancelled:
        return {"error": _("Bank \"{0}\" has been cancelled.").format(doc.name)}
    
    if not doc._is_auth:
        return {"error": _("Bank \"{0}\" isn't authorized.").format(doc.name)}
    
    row = None
    for v in doc.bank_accounts:
        if v.account == account:
            row = frappe._dict(v.as_dict(
                convert_dates_to_str=True,
                no_child_table_fields=True
            ))
            break
    
    if not row:
        return {"error": _("Bank account \"{0}\" doesn't belong to bank \"{1}\".").format(account, doc.name)}
    
    from .bank_account import AccountStatus
    
    if row.status != AccountStatus.re:
        return {
            "error": (
                _("Bank account \"{0}\" of bank \"{1}\" isn't ready.")
                .format(row.account, doc.name)
            )
        }
    
    if not row.bank_account_ref:
        return {
            "error": (
                _("Bank account \"{0}\" of bank \"{1}\" hasn't been added to ERPNext.")
                .format(row.account, doc.name)
            )
        }
    
    from .cache import get_cache
    
    if get_cache(_SYNC_KEY_, row.account):
        return {"info": _("Bank account \"{0}\" is already syncing in background.").format(row.account)}
    
    from .datetime import (
        today_date,
        date_to_datetime
    )
    
    today = today_date()
    doc = frappe._dict(doc.as_dict(
        convert_dates_to_str=True,
        no_child_table_fields=True
    ))
    if not can_sync_transactions(doc, row, date_to_datetime(today, start=True)):
        return {"info": _("Bank account \"{0}\" has exceeded the allowed sync limit for today.").format(row.account)}
    
    from .system import get_client
    
    client = get_client(doc.company, settings)
    if isinstance(client, dict):
        return client
    
    from .datetime import (
        reformat_date,
        is_date_gte,
        dates_diff_days
    )
    
    if not from_dt:
        from_dt = today
    else:
        from_dt = reformat_date(from_dt)
        if not from_dt or not is_date_gte(today, from_dt):
            from_dt = today
        
    if from_dt == today or not to_dt:
        to_dt = None
    
    if to_dt:
        to_dt = reformat_date(to_dt)
        if (
            not to_dt or
            from_dt == to_dt or
            is_date_gte(to_dt, today) or
            is_date_gte(from_dt, to_dt)
        ):
            to_dt = None
        
        elif dates_diff_days(from_dt, to_dt) > doc.transaction_days:
            from .datetime import add_date
            
            to_dt = add_date(from_dt, days=doc.transaction_days, as_string=True)
    
    if from_dt == today:
        diff_dt = 1
    else:
        diff_dt = dates_diff_days(from_dt, to_dt or today)
        diff_dt += 1
    
    settings = frappe._dict(settings.as_dict(
        convert_dates_to_str=True,
        no_child_table_fields=True
    ))
    if not queue_bank_transactions_sync(settings, client, doc, row, from_dt, to_dt, diff_dt, today, False):
        return {"info": _("Bank account \"{0}\" is already syncing in background.").format(row.account)}
    
    return {"success": _("Bank account \"{0}\" is syncing in background.").format(row.account)}


# [Schedule, Internal]
def can_sync_transactions(doc, row, today):
    from .sync_log import get_total_sync_logs
    
    total = get_total_sync_logs(doc.name, row.account, today)
    if total >= _SYNC_LIMIT:
        _store_info({
            "error": "Sync exceeded the allowed limit.",
            "bank": doc.name,
            "account_bank": doc.bank,
            "account": row.account,
            "limit": _SYNC_LIMIT
        })
        return 0
    
    return 1


# [Schedule, Internal]
def queue_bank_transactions_sync(settings, client, doc, row, from_dt, to_dt, diff_dt, today, auto: bool):
    from .background import is_job_running
    
    job_id = f"gocardless-bank-transactions-sync-{row.account}"
    if is_job_running(job_id):
        return 0
    
    from .background import enqueue_job
    from .cache import set_cache
    from .sync_log import LogTrigger, add_sync_data
    
    set_cache(_SYNC_KEY_, row.account, True)
    sync = add_sync_data(doc.name, row.account, from_dt, to_dt or today, LogTrigger.a if auto else LogTrigger.m)
    enqueue_job(
        "erpnext_gocardless_bank.libs.bank_transaction.sync_bank_transactions",
        job_id,
        queue="long",
        timeout=diff_dt * 60 * 1000,
        settings=settings,
        client=client,
        sync=sync,
        doc=doc,
        row=row,
        from_dt=from_dt,
        to_dt=to_dt
    )
    return 1


# [Internal]
def sync_bank_transactions(settings, client, sync, doc, row, from_dt, to_dt):
    result = frappe._dict({
        "entries": [],
        "synced": False,
        "last_sync": None
    })
    transactions = client.get_account_transactions(row.account, row.account_id, from_dt, to_dt)
    if "error" in transactions:
        if transactions.get("sent", 0):
            result.last_sync = get_last_sync_datetime(to_dt)
            update_bank_account_sync(client, row, result)
        
        finish_sync_bank_transactions(sync, row)
        _emit_sync_error({
            "error": transactions["error"],
            "name": doc.name,
            "bank": doc.bank,
            "bank_ref": doc.bank_ref,
            "account_ref": row.bank_account_ref
        })
        return 0
    
    from .sync_log import ongoing_sync_status
    
    ongoing_sync_status(sync)
    result.last_sync = get_last_sync_datetime(to_dt)
    
    try:
        for k in ["booked", "pending"]:
            if transactions.get(k, 0) and isinstance(transactions[k], list):
                _store_info({
                    "info": "Processing bank transactions.",
                    "type": k,
                    "account": row.account,
                    "data": transactions[k].copy()
                })
                
                result.synced = True
                add_transactions(
                    result, settings, sync, doc, row, k,
                    client.prepare_entries(transactions.pop(k))
                )
            else:
                _store_info({
                    "info": "Skipping bank transactions.",
                    "type": k,
                    "account": row.account,
                    "data": transactions.get(k, [])
                })
    finally:
        from .cache import clear_doc_cache
        
        update_bank_account_sync(client, row, result)
        finish_sync_bank_transactions(sync, row)
        clear_doc_cache("Bank Transaction")


# [Internal]
def get_last_sync_datetime(to_dt):
    if to_dt:
        from .datetime import date_to_datetime
        
        return date_to_datetime(to_dt)
    
    from .datetime import today_datetime
        
    return today_datetime()


# [Internal]
def update_bank_account_sync(client, row, result):
    from .bank_account import update_bank_account_data
    
    values = {"last_sync": result.last_sync}
    if result.synced:
        balances = client.get_account_balances(row.account_id)
        if balances and "error" not in balances:
            from .common import to_json
            
            values["balances"] = to_json(balances)
    
    update_bank_account_data(row.name, values)


# [Internal]
def finish_sync_bank_transactions(sync, row):
    from .cache import del_cache
    from .sync_log import finish_sync_status
    
    finish_sync_status(sync)
    del_cache(_SYNC_KEY_, row.account)


# [Internal]
def add_transactions(result, settings, sync, doc, row, status, transactions):
    old = len(result.entries)
    for i in range(len(transactions)):
        new_bank_transaction(result, settings, doc, row, status, transactions.pop(0))
    
    if len(result.entries) > old:
        from .sync_log import update_sync_total
        
        update_sync_total(sync, len(result.entries))


# [Internal]
def new_bank_transaction(result, settings, doc, row, status, data):
    entry = {
        "transaction_id": None,
        "date": None,
        "deposit": 0.0,
        "withdrawal": 0.0,
        "currency": None
    }
    ign = "Ignore"
    if data.get("transaction_id", ""):
        entry["transaction_id"] = data["transaction_id"]
    else:
        if settings.bank_transaction_without_id == ign:
            _store_info({
                "error": "Transaction has no id so ignored.",
                "account_bank": doc.bank,
                "account": row.account,
                "account_currency": row.account_currency,
                "bank_account_ref": row.bank_account_ref,
                "status": status,
                "data": data
            })
            data.clear()
            entry.clear()
            return 0
    
    if data.get("date", ""):
        from .datetime import reformat_date
        
        entry["date"] = reformat_date(data["date"])
    
    if not entry["date"]:
        if settings.bank_transaction_without_date == ign:
            _store_info({
                "error": "Transaction has no date so ignored.",
                "account_bank": doc.bank,
                "account": row.account,
                "account_currency": row.account_currency,
                "bank_account_ref": row.bank_account_ref,
                "status": status,
                "data": data
            })
            data.clear()
            entry.clear()
            return 0
        
        from .datetime import today_datetime
        
        entry["date"] = today_datetime()
    
    if "amount" in data:
        from frappe.utils import flt
        
        val = flt(data["amount"])
        entry["deposit"] = abs(val) if val >= 0.0 else 0.0
        entry["withdrawal"] = abs(val) if val < 0.0 else 0.0
    else:
        if settings.bank_transaction_without_amount == ign:
            _store_info({
                "error": "Transaction has no amount so ignored.",
                "account_bank": doc.bank,
                "account": row.account,
                "account_currency": row.account_currency,
                "bank_account_ref": row.bank_account_ref,
                "status": status,
                "data": data
            })
            data.clear()
            entry.clear()
            return 0
    
    if not data.get("currency", ""):
        if settings.bank_transaction_without_currency == ign:
            _store_info({
                "error": "Transaction has no currency so ignored.",
                "account_bank": doc.bank,
                "account": row.account,
                "account_currency": row.account_currency,
                "bank_account_ref": row.bank_account_ref,
                "status": status,
                "data": data
            })
            data.clear()
            entry.clear()
            return 0
        
        entry["currency"] = row.account_currency
    else:
        from .currency import get_currency_status
        
        entry["currency"] = data["currency"]
        currency_status = get_currency_status(data["currency"])
        if currency_status is None:
            if settings.bank_transaction_currency_doesnt_exist == ign:
                _store_info({
                    "error": "Transaction currency doesn't exist so ignored.",
                    "account_bank": doc.bank,
                    "account": row.account,
                    "account_currency": row.account_currency,
                    "bank_account_ref": row.bank_account_ref,
                    "status": status,
                    "data": data
                })
                data.clear()
                entry.clear()
                return 0
            
            from .currency import add_currencies
            
            add_currencies([data["currency"]])
        
        elif not currency_status:
            if settings.bank_transaction_currency_disabled == ign:
                _store_info({
                    "error": "Transaction currency is disabled so ignored.",
                    "account_bank": doc.bank,
                    "account": row.account,
                    "account_currency": row.account_currency,
                    "bank_account_ref": row.bank_account_ref,
                    "status": status,
                    "data": data
                })
                data.clear()
                entry.clear()
                return 0
            
            from .currency import enable_currencies
            
            enable_currencies([data["currency"]])
    
    if not entry["transaction_id"]:
        from .common import unique_key
        
        entry["transaction_id"] = unique_key(data)
    
    dt = "Bank Transaction"
    if not frappe.db.exists(dt, {"transaction_id": entry["transaction_id"]}):
        try:
            entry.update({
                "status": "Pending" if status == "pending" else "Settled",
                "bank_account": row.bank_account_ref,
                "description": data.get("description", ""),
                "gocardless_transaction_info": data.get("information", ""),
                "reference_number": data.get("reference_number", ""),
                "from_gocardless": 1
            })
            
            handle_transaction_supplier(settings, doc.company, entry, doc.bank, data)
            handle_transaction_customer(settings, doc.company, entry, doc.bank, data)
            
            doc = frappe.new_doc(dt)
            doc.update(entry)
            doc.insert(ignore_permissions=True, ignore_mandatory=True)
            doc.submit()
            result.entries.append(doc.name)
        except Exception as exc:
            _store_error({
                "error": "Unable to add new transaction.",
                "account_bank": doc.bank,
                "account": row.account,
                "account_currency": row.account_currency,
                "bank_account_ref": row.bank_account_ref,
                "status": status,
                "data": data,
                "exception": str(exc)
            })
    
    data.clear()
    entry.clear()


# [Internal]
def handle_transaction_supplier(settings, company, entry, account_bank, data):
    ign = "Ignore"
    if (
        settings.supplier_exist_in_transaction == ign or
        not data.get("supplier", "") or
        not isinstance(data["supplier"], dict) or
        not data["supplier"].get("name", "") or
        not isinstance(data["supplier"]["name"], str)
    ):
        return 0
    
    from .supplier import is_supplier_exist
    
    name = data["supplier"]["name"]
    ignore_supplier = False
    if not is_supplier_exist(name):
        if (
            settings.supplier_in_transaction_doesnt_exist == ign or
            not settings.supplier_default_group
        ):
            return 0
        
        from .supplier import add_new_supplier
        
        ret = add_new_supplier(name, settings.supplier_default_group)
        if "error" not in ret:
            entry["party_type"] = ret["dt"]
            entry["party"] = ret["name"]
        else:
            _store_error({
                "error": "Unable to create new supplier.",
                "data": data["supplier"],
                "exception": ret["error"]
            })
            ignore_supplier = True
    
    else:
        from .supplier import get_supplier_name
        
        ret = get_supplier_name(name)
        if ret:
            entry["party_type"] = ret["dt"]
            entry["party"] = ret["name"]
        else:
            _store_error({
                "error": "Unable to get supplier name.",
                "data": data["supplier"]
            })
            ignore_supplier = True
    
    if (
        ignore_supplier or
        settings.supplier_bank_account_exist_in_transaction == ign or
        not data["supplier"].get("account", "") or
        not isinstance(data["supplier"]["account"], str)
    ):
        return 0
    
    from .bank_account import add_party_bank_account
    
    acc_name = add_party_bank_account(
        name, entry["party_type"],
        account_bank, company,
        data["supplier"]["account"],
        data["supplier"].get("account_no", ""),
        data["supplier"].get("iban", "")
    )
    if acc_name:
        from .supplier import set_supplier_bank_account
        
        set_supplier_bank_account(entry["party"], acc_name)


# [Internal]
def handle_transaction_customer(settings, company, entry, account_bank, data):
    ign = "Ignore"
    if (
        settings.customer_exist_in_transaction == ign or
        entry.get("party_type", "") or
        entry.get("party", "") or
        not data.get("customer", "") or
        not isinstance(data["customer"], dict) or
        not data["customer"].get("name", "") or
        not isinstance(data["customer"]["name"], str)
    ):
        return 0
    
    from .customer import is_customer_exist
    
    name = data["customer"]["name"]
    ignore_customer = False
    if not is_customer_exist(name):
        if (
            settings.customer_in_transaction_doesnt_exist == ign or
            not settings.customer_default_group or
            not settings.customer_default_territory
        ):
            return 0
        
        from .customer import add_new_customer
        
        ret = add_new_customer(name, settings.customer_default_group, settings.customer_default_territory)
        if "error" not in ret:
            entry["party_type"] = ret["dt"]
            entry["party"] = ret["name"]
        else:
            _store_error({
                "error": "Unable to create new customer.",
                "data": data["customer"],
                "exception": ret["error"]
            })
            ignore_customer = True
    
    else:
        from .customer import get_customer_name
        
        ret = get_customer_name(name)
        if ret:
            entry["party_type"] = ret["dt"]
            entry["party"] = ret["name"]
        else:
            _store_error({
                "error": "Unable to get customer name.",
                "data": data["customer"]
            })
            ignore_customer = True
    
    if (
        ignore_customer or
        settings.customer_bank_account_exist_in_transaction == ign or
        not data["customer"].get("account", "") or
        not isinstance(data["customer"]["account"], str)
    ):
        return 0
    
    from .bank_account import add_party_bank_account
    
    acc_name = add_party_bank_account(
        name, entry["party_type"],
        account_bank, company,
        data["customer"]["account"],
        data["customer"].get("account_no", ""),
        data["customer"].get("iban", "")
    )
    if acc_name:
        from .customer import set_customer_bank_account
        
        set_customer_bank_account(entry["party"], acc_name)


# [Internal]
def _store_error(data):
    from .common import store_error
    
    store_error(data)


# [Internal]
def _store_info(data):
    from .common import store_info
    
    store_info(data)


# [Internal]
def _emit_sync_error(data):
    from .realtime import emit_bank_account_sync_error
    
    emit_bank_account_sync_error(data)