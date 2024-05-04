# ERPNext ERPNext Gocardless Bank © 2023
# Author:  Ameen Ahmed
# Company: Level Up Marketing & Software Development Services
# Licence: Please refer to LICENSE file


from datetime import datetime
import hashlib
import uuid

import frappe
from frappe import _, _dict
from frappe.utils import (
    cint,
    flt,
    get_datetime,
    add_to_date,
    formatdate,
    getdate,
    DATE_FORMAT,
    DATETIME_FORMAT
)

from erpnext_gocardless_bank.version import __frappe_version_min_15__
from .gocardless_common import (
    error,
    log_error,
    log_info,
    to_json
)
from .gocardless_connector import GocardlessConnector


_SETTINGS_ = "Gocardless Settings"
_BANK_ = "Gocardless Bank"
_BANK_ACCOUNT_ = "Gocardless Bank Account"
_SYNC_LOG_ = "Gocardless Sync Log"
_SYNC_LIMIT = 4
_SYNC_CACHE_KEY = "gocardless_auto_sync"


def clear_sync_cache():
    frappe.cache().delete_key(_SYNC_CACHE_KEY)


def report_error(data, _throw=True):
    if "list" not in data:
        data = {"list": [data]}
    if "list" in data:
        if not isinstance(data["list"], list):
            data["list"] = [data["list"]]
        errors = []
        raw = []
        for row in data["list"]:
            msg = []
            if "title" in row:
                msg.append(_(row["title"]))
            if "message" in row:
                msg.append(_(row["message"]))
            if msg:
                errors.append(": ".join(msg))
            else:
                raw.append(row)
        if not errors:
            errors.append("An error has occurred but the error format is invalid.")
        if errors:
            error(". ".join(errors) + ".", _throw, "cVavguDT4p")
        if raw:
            log_error(raw)


def clear_doc_cache(dt=None, name=None):
    if dt is None:
        dt = _SETTINGS_
    if name is None:
        name = dt
    frappe.clear_cache(doctype=dt)
    frappe.clear_document_cache(dt, name)
    frappe.cache().delete_key(dt)


def get_cached_doc(dt, name=None, for_update=False):
    if isinstance(name, bool):
        for_update = name
        name = None
    if name is None:
        name = dt
    if for_update:
        clear_doc_cache(dt, name)
    return frappe.get_cached_doc(dt, name, for_update=for_update)


def get_doc(for_update=False):
    return get_cached_doc(_SETTINGS_, for_update=for_update)


# Gocardless
@frappe.whitelist()
def is_enabled():
    return cint(getattr(get_doc(), "enabled", 0)) == 1


def get_client():
    doc = get_doc()
    now_dt = datetime.utcnow()
    client = GocardlessConnector()
    if doc.access_token and get_datetime(doc.access_expiry) > now_dt:
        client.set_access(doc.access_token)
        return client
    
    if doc.refresh_token and get_datetime(doc.refresh_expiry) > now_dt:
        client.refresh(doc.refresh_token)
    else:
        client.connect(doc.secret_id, doc.secret_key)
    
    doc = get_doc(True)
    access = client.get_access()
    if "refresh" in access:
        doc.refresh_token = access["refresh"]
        doc.refresh_expiry = add_to_date(
            now_dt,
            seconds=cint(access["refresh_expires"]),
            as_string=True,
            as_datetime=True
        )
    
    doc.access_token = access["access"]
    doc.access_expiry = add_to_date(
        now_dt,
        seconds=cint(access["access_expires"]),
        as_string=True,
        as_datetime=True
    )
    doc.save(ignore_permissions=True)
    return client


# Gocardless Bank Form
@frappe.whitelist()
def get_banks(country=None, pay_option=False):
    if not is_enabled():
        return []
    
    if not isinstance(country, str):
        country = None
    elif country:
        country = get_country_code(country) if len(country) > 2 else country.upper()
    
    return get_client().get_banks(country, pay_option)


def get_country_code(country):
    return frappe.db.get_value('Country', country, 'code').upper()


# Gocardless
@frappe.whitelist(methods=["POST"])
def get_bank_link(bank_id, reference_id, transaction_days, docname = None):
    if not is_enabled():
        return {}
    return get_client().get_bank_link(
        bank_id, reference_id, cint(transaction_days), docname
    )


# Gocardless Bank List
@frappe.whitelist(methods=["POST"])
def save_bank_link(name, auth_id, auth_expiry):
    if not is_enabled():
        return 0
    
    if (
        not name or not isinstance(name, str) or
        not auth_id or not isinstance(auth_id, str) or
        not auth_expiry or not isinstance(auth_expiry, str)
    ):
        return 0
    
    frappe.get_doc(_BANK_, name).save_link(auth_id, auth_expiry)
    return 1


# Gocardless Bank
def enqueue_save_bank(docname, bank, auth_id):
    if __frappe_version_min_15__:
        frappe.enqueue(
            "erpnext_gocardless_bank.libs.gocardless.save_bank",
            job_id=f"gocardless-save-bank-{bank}",
            is_async=True,
            enqueue_after_commit=False,
            docname=docname,
            bank=bank,
            auth_id=auth_id
        )
    else:
        frappe.enqueue(
            "erpnext_gocardless_bank.libs.gocardless.save_bank",
            job_name=f"gocardless-save-bank-{bank}",
            is_async=True,
            enqueue_after_commit=False,
            docname=docname,
            bank=bank,
            auth_id=auth_id
        )


# Gocardless Bank
def enqueue_update_bank(docname, bank, auth_id):
    if __frappe_version_min_15__:
        frappe.enqueue(
            "erpnext_gocardless_bank.libs.gocardless.update_bank",
            job_id=f"gocardless-update-bank-{bank}",
            is_async=True,
            enqueue_after_commit=False,
            docname=docname,
            bank=bank,
            auth_id=auth_id
        )
    else:
        frappe.enqueue(
            "erpnext_gocardless_bank.libs.gocardless.update_bank",
            job_name=f"gocardless-update-bank-{bank}",
            is_async=True,
            enqueue_after_commit=False,
            docname=docname,
            bank=bank,
            auth_id=auth_id
        )


# Internal
def save_bank(docname, bank, auth_id):
    if add_bank(bank):
        if (accounts := get_client_bank_accounts(bank, auth_id, False)):
            result = prepare_bank_accounts(accounts, bank)
            store_bank_accounts(docname, result)
        else:
            send_bank_error(
                {
                    "name": docname,
                    "bank": bank,
                    "error": _(
                        "There was an error while " +
                        "creating or updating bank accounts of {0}."
                    ).format(bank)
                }
            )


# Internal
def add_bank(bank):
    dt = "Bank"
    if not frappe.db.exists(dt, bank):
        try:
            (frappe.new_doc(dt)
                .update({"bank_name": bank})
                .insert(ignore_permissions=True, ignore_mandatory=True))
        except Exception as exc:
            log_error(exc)
            err = _("Unable to add the bank \"{0}\".").format(bank)
            error(err, False, "UUnGD5uWme")
            send_bank_error(
                {"bank": bank, "error": err},
                report=False
            )
            return 0
        
        clear_doc_cache(dt)
    
    return 1


# Internal
def get_client_bank_accounts(bank, auth_id, publish = True):
    client = get_client()
    accounts = client.get_accounts(auth_id)
    if "error" in accounts:
        report_error(accounts, False)
        if publish:
            send_bank_error(
                {
                    "bank": bank,
                    "error": _(
                        "Unable to get the bank accounts of \"{0}\" from api"
                    ).format(bank)
                },
                report=False
            )
        return 0
    
    data = []
    for v in accounts:
        acc_data = client.get_account_data(v)
        if "error" in acc_data:
            report_error(acc_data, False)
            continue
            
        acc_balances = client.get_account_balances(v)
        if "error" in acc_balances:
            report_error(acc_balances, False)
            continue
        
        acc_details = client.get_account_details(v)
        if "error" in acc_details:
            report_error(acc_details, False)
            continue
        
        account = {"id": v}
        account.update(acc_data)
        account.update({"balances": to_json(acc_balances)})
        account.update(acc_details)
        data.append(account)
    
    return data


# Internal
def prepare_bank_accounts(accounts, bank):
    name_level = 1
    names_list = []
    name_duplicate = 0
    currencies_list = []
    currency_duplicate = 0
    currency_not_found = 0
    names_idx = 1
    result = []
    
    for acc in accounts:
        if "name" not in acc:
            acc["name"] = bank + " Account"
        
        if acc["name"] not in names_list:
            names_list.append(acc["name"])
        else:
            name_duplicate = 1
        
        if "currency" in acc:
            if acc["currency"] not in currencies_list:
                currencies_list.append(acc["currency"])
            else:
                currency_duplicate = 1
        else:
            currency_not_found = 1
    
    if name_duplicate:
        if not currency_duplicate and not currency_not_found:
            name_level = 2
        elif currency_duplicate and not currency_not_found:
            name_level = 3
        else:
            name_level = 4
    
    for acc in accounts:
        if name_level == 2:
            acc["name"] = "{0} - {1}".format(
                acc["name"], str(acc["currency"]).upper()
            )
        elif name_level == 3:
            acc["name"] = "{0} - {1} - {2}".format(
                acc["name"], str(acc["currency"]).upper(), names_idx
            )
            names_idx += 1
        elif name_level == 4:
            acc["name"] = "{0} - {1}".format(
                acc["name"], names_idx
            )
            names_idx += 1
        
        iban = acc.get("iban", "")
        if iban and not is_valid_IBAN(iban):
            acc["iban"] = ""
        
        result.append({
            "account": acc["name"],
            "account_id": acc["id"],
            "account_type": acc.get("cashAccountType", ""),
            "account_no": acc.get("resourceId", ""),
            "iban": acc.get("iban", ""),
            "balances": acc["balances"],
            "status": acc["status"],
            "bank_account": "",
        })
    
    return result


# Gocardless Bank
def add_bank_account(docname, company, bank, account):
    if account["account_type"]:
        if (has_error := add_account_type(account["account_type"])):
            send_bank_error(
                {
                    "bank": bank,
                    "error": _(
                        "Unable to create the bank account type \"{0}\"."
                    ).format(account["account_type"]),
                    "account": account["account"],
                    "account_type": account["account_type"],
                }
            )
            return 0
    
    has_error = 0
    err = ""
    dt = "Bank Account"
    bank_account_name = make_bank_account_name(account["account"], bank)
    if not frappe.db.exists(dt, bank_account_name):
        try:
            (frappe.new_doc(dt)
                .update({
                    "account_name": account["account"],
                    "bank": bank,
                    "account_type": account["account_type"],
                    "gocardless_bank_account_no": account["account_no"],
                    "company": company,
                    "iban": account["iban"],
                    "is_default": account["is_default"],
                })
                .insert(ignore_permissions=True, ignore_mandatory=True))
        except frappe.UniqueValidationError:
            has_error = 1
            err = _(
                "The bank account \"{0}\" already exists."
            ).format(account["account"])
        except Exception as exc:
            has_error = 1
            err = _(
                "Unable to add the bank account \"{0}\" of " +
                "the Gocardless bank \"{1}\" to ERPNext."
            ).format(account["account"], bank)
            log_error(exc)

    else:
        try:
            (get_cached_doc(dt, bank_account_name, True)
            .update({
                "account_name": account["account"],
                "bank": bank,
                "account_type": account["account_type"],
                "gocardless_bank_account_no": account["account_no"],
                "company": company,
                "iban": account["iban"],
                "is_default": account["is_default"],
            })
            .save(ignore_permissions=True))
        except Exception as exc:
            has_error = 1
            err = _(
                "Unable to update the bank account \"{0}\" of " +
                "the Gocardless bank \"{1}\" in ERPNext."
            ).format(account["account"], bank)
            log_error(exc)
    
    if not has_error:
        if (has_error := update_bank_account(
            docname, bank_account_name, account["account"]
        )):
            err = _(
                "Unable to update the bank account \"{0}\" data of " +
                "Gocardless bank \"{1}\"."
            ).format(account["account"], bank)
    
    clear_doc_cache(dt)
    
    if has_error:
        send_bank_error(
            {
                "bank": bank,
                "error": err,
                "account": account["account"],
            }
        )
        return 0
    
    return 1


def make_bank_account_name(name, bank):
    return "{0} - {1}".format(name, bank)


# Internal
def add_account_type(name):
    dt = "Bank Account Type"
    if not frappe.db.exists(dt, name):
        try:
            (frappe.new_doc(dt)
                .update({"account_type": name})
                .insert(ignore_permissions=True, ignore_mandatory=True))
        except Exception as exc:
            log_error(exc)
            error(_("Unable to create {0} bank account type.").format(name), False, "v6qxeg8M5m")
            return 1
        
        clear_doc_cache(dt)
    
    return 0


# Internal
def store_bank_accounts(docname, accounts):
    doc = get_cached_doc(_BANK_, docname, True)
    existing = {v.account:v for v in doc.bank_accounts}
    added = []
    for row in accounts:
        data = {}
        if row["account"] in existing:
            data.update(existing[row["account"]])
            doc.bank_accounts.remove(existing[row["account"]])
        else:
            data.update(row)
            added.append(row["account"])
        
        doc.append("bank_accounts", data)
    
    doc.save(ignore_permissions=True)
    
    frappe.publish_realtime(
        event="gocardless_reload_bank_accounts",
        message={"name": docname, "bank": doc.bank},
        after_commit=True
    )
    
    return added


# Gocardless Bank
# Internal
def update_bank_account(docname, bank_account, account):
    doc = get_cached_doc(_BANK_, docname, True)
    
    has_error = 1
    for v in doc.bank_accounts:
        if v.account == account and not getattr(v, "bank_account", ""):
            has_error = 0
            v.update({"bank_account": bank_account})
            doc.save(ignore_permissions=True)
            clear_doc_cache(_BANK_)
            break
    
    return has_error


# Gocardless Bank
# Internal
def send_bank_error(message, report=True, after_commit=True):
    if report:
        log_error(message["error"])
        error(message["error"], False, "5Gkg6HhmVY")
    
    frappe.publish_realtime(
        event="gocardless_bank_error",
        message=message,
        after_commit=after_commit
    )


# Gocardless Bank Form
@frappe.whitelist()
def get_bank_accounts_list():
    if (accounts := frappe.get_all(
        "Bank Account",
        fields=["name", "account_name"],
        filters={
            "docstatus": ["!=", 2],
        }
    )):
        return accounts
    
    return 0


# Internal
def update_bank(docname, bank, auth_id):
    if (accounts := get_client_bank_accounts(bank, auth_id)):
        result = prepare_bank_accounts(accounts, bank)
        doc = get_cached_doc(_BANK_, docname, True)
        existing = {v.account:v for v in doc.bank_accounts}
        updated = 0
        new_acc = []
        
        for v in result:
            if v["account"] not in existing:
                new_acc.append(v)
            else:
                updated = 1
                data = existing[v["account"]]
                data.update({"status": v["status"]})
                doc.append("bank_accounts", data)
        
        if updated:
            doc.save(ignore_permissions=True)
        
        if new_acc:
            log_info(_(
                "Bank link update of {0} returned {1} new bank accounts."
            ).format(bank, len(new_acc)))
            store_bank_accounts(docname, new_acc)
        else:
            frappe.publish_realtime(
                event="gocardless_reload_bank_accounts",
                message={"name": docname, "bank": bank},
                after_commit=True
            )


def is_bank_exist(bank, throw=True):
    if not frappe.db.exists(_BANK_, bank):
        if throw:
            error(_("The Gocardless bank {0} doesn't exist.").format(bank), code="czDbdS5YuV")
        return 0
    
    return 1


# Bank Account Form
@frappe.whitelist(methods=["POST"])
def get_bank_account_data(bank_account):
    if not is_enabled():
        return 0
    
    if (accounts := frappe.get_all(
        _BANK_ACCOUNT_,
        fields=["parent", "account", "status", "last_sync"],
        filters={
            "bank_account": bank_account,
            "parenttype": _BANK_,
            "parentfield": "bank_accounts",
        }
    )):
        if accounts[0]["status"] != "Ready":
            return {
                "bank_account": bank_account,
                "status": accounts[0]["status"]
            }
        
        return {
            "bank_account": bank_account,
            "bank": accounts[0]["parent"],
            "account": accounts[0]["account"],
            "status": accounts[0]["status"],
            "last_sync": accounts[0]["last_sync"]
        }
    
    return -1


# Gocardless Bank Form
# Bank Account Form
@frappe.whitelist(methods=["POST"])
def enqueue_bank_account_sync(bank, account, from_date=None, to_date=None):
    if not is_enabled():
        return -1
    
    if not is_bank_exist(bank):
        return -2
    
    doc = get_cached_doc(_BANK_, bank)
    accounts = {v.account:v for v in doc.bank_accounts}
    
    if account not in accounts:
        error(_(
            "The Gocardless bank account \"{0}\" is not part of {1}."
        ).format(account, bank), code="MgZDdh8xyM")
        return -3
    
    if frappe.cache().hget(_SYNC_CACHE_KEY, account):
        return 1
    
    now = datetime.utcnow()
    today = now.strftime(DATE_FORMAT)
    settings = get_settings()
    client = get_client()
    data = accounts[account]
    if from_date or to_date:
        if from_date:
            from_date = reformat_date(from_date, True)
        
        if to_date:
            to_date = reformat_date(to_date, True)
        
        if not from_date and to_date:
            from_date = add_to_date(
                datetime.strptime(to_date, DATE_FORMAT),
                days=-1,
                as_string=True
            )
        
        if not to_date and from_date:
            to_date = add_to_date(
                datetime.strptime(from_date, DATE_FORMAT),
                days=1,
                as_string=True
            )
        
        if from_date == today:
            from_date = None
        else:
            date_from_obj = datetime.strptime(from_date, DATE_FORMAT)
            date_delta = datetime.strptime(to_date, DATE_FORMAT) - date_from_obj
            date_diff = cint(date_delta.days)
            last_date = date_from_obj
            has_error = 0
            total = 0
            for i in range(0, date_diff, 2):
                total += 1
                if i > 0:
                    last_date = add_to_date(last_date, days=1)
                
                date_from = last_date.strftime(DATE_FORMAT)
                last_date = add_to_date(last_date, days=1)
                date_to = last_date.strftime(DATE_FORMAT)
                if not sync_bank_account(
                    settings, client, bank, doc.bank, "Manual",
                    data.name, data.account, data.account_id,
                    data.bank_account, date_from, date_to
                ):
                    has_error += 1
            
            if has_error:
                if has_error == total:
                    error(_(
                        "There was an error while syncing " +
                        "Gocardless bank account \"{0}\" of {1} from {2} to {3}."
                    ).format(
                        data.account, bank, from_date, to_date
                    ), False, "nMar7aW44f")
                    return 0
                else:
                    error(_(
                        "There was {0} errors while syncing " +
                        "Gocardless bank account \"{1}\" of {2} from {3} to {4}."
                    ).format(
                        has_error, data.account, bank, from_date, to_date
                    ), False, "tyHwW4S2tj")
            
            return 1
    
    if not from_date:
        to_date = add_to_date(now, days=1, as_string=True)
        if not sync_bank_account(
            settings, client, bank, doc.bank, "Manual",
            data.name, data.account, data.account_id,
            data.bank_account, today, to_date
        ):
            error(_(
                "There was an error while syncing " +
                "Gocardless bank account \"{0}\" of {1} from {2} to {3}."
            ).format(
                data.account, bank, today, to_date
            ), False, "A5S3FMCaYS")
            return 0
    
    return 1


# Every 6 Hours Schedule
def auto_sync():
    if is_enabled():
        sync_banks()


# Daily Schedule
def update_banks_status():
    if (banks := frappe.get_all(
        _BANK_,
        fields=["name"],
        filters={
            "auth_id": ["!=", ""],
            "auth_status": "Linked",
            "auth_expiry": ["<", datetime.utcnow().strftime(DATE_FORMAT)],
        },
        pluck="name"
    )):
        try:
            bDoc = frappe.qb.DocType(_BANK_)
            (
                frappe.qb.update(bDoc)
                .set(bDoc.auth_id, "")
                .set(bDoc.auth_expiry, "")
                .set(bDoc.auth_status, "Unlinked")
                .where(bDoc.name.isin(banks))
            ).run()
        except Exception as exc:
            log_error(exc)
            error(_("Unable to update Gocardless bank auth status"), False, "xYRxZTKz99")
        
        try:
            baDoc = frappe.qb.DocType(_BANK_ACCOUNT_)
            (
                frappe.qb.update(baDoc)
                .set(baDoc.status, "Expired")
                .where(baDoc.parent.isin(banks))
                .where(baDoc.parenttype == _BANK_)
                .where(baDoc.parentfield == "bank_accounts")
            ).run()
        except Exception as exc:
            log_error(exc)
            error(_("Unable to update Gocardless bank accounts status"), False, "Jma9mRWrBD")
        
        frappe.publish_realtime(
            event="gocardless_updated_bank_accounts",
            after_commit=True
        )
    
    update_bank_accounts_status()


# Internal
# Part of Daily Schedule
def update_bank_accounts_status():
    if (banks := frappe.get_all(
        _BANK_,
        fields=["name"],
        filters={
            "auth_id": ["!=", ""],
            "auth_status": "Linked",
        },
        pluck="name"
    )):
        if (accounts := frappe.get_all(
            _BANK_ACCOUNT_,
            fields=["parent", "name", "account", "account_id", "status"],
            filters={
                "parent": ["in", banks],
                "parenttype": _BANK_,
                "parentfield": "bank_accounts",
                "status": ["!=", "Ready"]
            }
        )):
            client = get_client()
            for v in accounts:
                data = client.get_account_data(v["account_id"])
                if "error" in data:
                    report_error(data, False)
                    continue
                
                if data["status"] != v["status"]:
                    values = {"status": data["status"]}
                    
                    if data["status"] == "Ready":
                        acc_balances = client.get_account_balances(v["account_id"])
                        if "error" in acc_balances:
                            report_error(acc_balances, False)
                        else:
                            values.update({"balances": to_json(acc_balances)})
                    
                    try:
                        frappe.db.set_value(
                            _BANK_ACCOUNT_,
                            v["name"],
                            values,
                            update_modified=False
                        )
                    except Exception as exc:
                        log_error(exc)
                        error(_(
                            "Unable to update account status of {0} for {1}"
                        ).format(v["account"], v["parent"]), False, "5Gg8e9sPEh")
        
            frappe.publish_realtime(
                event="gocardless_updated_bank_accounts",
                after_commit=True
            )


# Internal
def sync_banks():
    filters = {
        "disabled": 0,
        "auto_sync": 1,
        "auth_id": ["!=", ""],
        "auth_status": "Linked",
        "auth_expiry": [">=", datetime.utcnow().strftime(DATE_FORMAT)],
    }
    
    if (banks := frappe.get_all(
        _BANK_,
        fields=["name"],
        filters=filters,
        pluck="name"
    )):
        for bank in banks:
            sync_bank(bank, "Auto")


# Internal
def sync_bank(name, trigger):
    now = datetime.utcnow()
    today = now.strftime(DATE_FORMAT)
    doc = get_cached_doc(_BANK_, name)
    settings = get_settings()
    client = get_client()
    for v in doc.bank_accounts:
        if v.status != "Ready":
            log_info("The bank account {0} of {1} is not ready.".format(
                v.account, doc.bank
            ))
            continue
        
        if frappe.cache().hget(_SYNC_CACHE_KEY, v.account):
            log_info("The bank account {0} of {1} is already being synced.".format(
                v.account, doc.bank
            ))
            continue
        
        date_from = None
        date_to = today
        
        if v.last_sync:
            date_from = reformat_date(v.last_sync)
            if date_from == today:
                date_from = None
            else:
                date_from_obj = datetime.strptime(date_from, DATE_FORMAT)
                date_delta = datetime.strptime(date_to, DATE_FORMAT) - date_from_obj
                if cint(date_delta.days) > 1:
                    date_to = add_to_date(date_from_obj, days=1, as_string=True)
        
        if not date_from:
            date_from = add_to_date(now, days=-1, as_string=True)
        
        if not sync_bank_account(
            settings, client, name, doc.bank, trigger,
            v.name, v.account, v.account_id,
            v.bank_account, date_from, date_to
        ):
            return 0


# Internal
def reformat_date(date: str, def_none=False):
    try:
        formatted_date = formatdate(date, DATE_FORMAT)
    except Exception:
        formatted_date = None
    
    if not formatted_date:
        try:
            formatted_date = getdate(date);
            if formatted_date:
                formatted_date = formatted_date.strftime(DATE_FORMAT)
        except Exception:
            formatted_date = None
    
    if formatted_date:
        return formatted_date
    
    if def_none:
        return None
    
    return datetime.utcnow().strftime(DATE_FORMAT)


# Internal
def get_settings():
    cache = frappe.cache().hget(_SETTINGS_, "prep")
    if cache and isinstance(cache, dict):
        return cache
    
    doc = _dict(get_doc().as_dict())
    for k in [
        "only_sync_transactions_with_id",
        "ignore_transactions_without_date",
        "ignore_transactions_without_amount",
        "ignore_transactions_without_currency",
        "ignore_transactions_without_existing_currency",
        "ignore_transactions_without_enabled_currency",
        "add_supplier_info_if_available",
        "create_supplier_if_does_not_exist",
        "create_supplier_bank_account_if_does_not_exist",
        "add_customer_info_if_available",
        "create_customer_if_does_not_exist",
        "create_customer_bank_account_if_does_not_exist",
    ]:
        doc[k] = True if cint(doc[k]) else False
    
    frappe.cache().hset(_SETTINGS_, "prep", doc)
    return doc


# Internal
def sync_bank_account(
    settings, client, bank, account_bank, trigger,
    account_name, account, account_id, bank_account,
    date_from, date_to
):
    today = datetime.utcnow().strftime(DATE_FORMAT)
    sync_data = frappe.get_all(
        _SYNC_LOG_,
        fields=["sync_id"],
        filters={
            "bank": bank,
            "bank_account": account,
            "modified": ["between", [today + " 00:00:00", today + " 23:59:59"]]
        },
        distinct=True
    )
    
    if not isinstance(sync_data, list):
        log_info((
            "The sync log data of the bank account {0} that belongs to {1} is invalid."
        ).format(account, account_bank))
        return 0
    
    if len(sync_data) >= _SYNC_LIMIT:
        log_info((
            "The synchronization for the bank account {0} "
            + "of {1} has exceeded the allowed limit {2}."
        ).format(account, account_bank, _SYNC_LIMIT))
        return 0
    
    log_info((
        "The sync transactions for the bank account {0} of {1} has been queued."
    ).format(account, account_bank))
    
    if __frappe_version_min_15__:
        frappe.enqueue(
            "erpnext_gocardless_bank.libs.gocardless.sync_bank_account_transactions",
            job_id="gocardless-sync-bank-account-transactions-" + account,
            queue="long",
            is_async=True,
            enqueue_after_commit=False,
            settings=settings,
            client=client,
            sync_id=uuid.uuid4(),
            bank=bank,
            acc_bank=account_bank,
            trigger=trigger,
            account_name=account_name,
            account=account,
            account_id=account_id,
            bank_account=bank_account,
            date_from=date_from,
            date_to=date_to
        )
    else:
        frappe.enqueue(
            "erpnext_gocardless_bank.libs.gocardless.sync_bank_account_transactions",
            job_name="gocardless-sync-bank-account-transactions-" + account,
            queue="long",
            is_async=True,
            enqueue_after_commit=False,
            settings=settings,
            client=client,
            sync_id=uuid.uuid4(),
            bank=bank,
            acc_bank=account_bank,
            trigger=trigger,
            account_name=account_name,
            account=account,
            account_id=account_id,
            bank_account=bank_account,
            date_from=date_from,
            date_to=date_to
        )
    
    return 1


# Internal
def sync_bank_account_transactions(
    settings, client, sync_id, bank, acc_bank, trigger,
    account_name, account, account_id, bank_account,
    date_from, date_to
):
    if frappe.cache().hget(_SYNC_CACHE_KEY, account):
        return 0
    
    frappe.cache().hset(_SYNC_CACHE_KEY, account, True)
    
    log_info("Bank account transactions sync for {0} has started.".format(account))
    
    transactions = client.get_account_transactions(account_id, date_from, date_to)
    
    if transactions and "error" in transactions:
        frappe.cache().hdel(_SYNC_CACHE_KEY, account)
        report_error(transactions, False)
        return 0
    
    result = _dict({
        "entries": [],
        "synced": False,
    })
    
    try:
        if transactions:
            log_info((
                "Bank account transactions for {0} has been received from api."
            ).format(account))
            for k in ["booked", "pending"]:
                if (
                    k in transactions and transactions[k] and
                    isinstance(transactions[k], list)
                ):
                    log_info((
                        "Processing the {0} transactions for bank account \"{1}\"."
                    ).format(k, account))
                    log_info(transactions[k])
                    
                    add_transactions(
                        result, settings, sync_id, bank, acc_bank, trigger,
                        account, bank_account, k,
                        client.prepare_entries(transactions.pop(k)),
                        date_from, date_to
                    )
                else:
                    log_info((
                        "Skipping the {0} transactions for bank account \"{1}\"."
                    ).format(k, account))
    finally:
        
        if result.synced:
            last_sync = datetime.combine(
                datetime.strptime(date_to, DATE_FORMAT),
                datetime.utcnow().time()
            ).strftime(DATETIME_FORMAT)
            values = {"last_sync": last_sync}
            
            acc_balances = client.get_account_balances(account_id)
            if "error" in acc_balances:
                report_error(acc_balances, False)
            else:
                values.update({"balances": to_json(acc_balances)})
            
            frappe.db.set_value(
                _BANK_ACCOUNT_,
                account_name,
                values,
                update_modified=False
            )
        
        (frappe.new_doc(_SYNC_LOG_)
            .update({
                "sync_id": sync_id,
                "bank": bank,
                "bank_account": account,
                "trigger": trigger,
                "total_transactions": len(result.entries),
            })
            .insert(ignore_permissions=True, ignore_mandatory=True))
        
        frappe.cache().hdel(_SYNC_CACHE_KEY, account)
        
        clear_doc_cache("Bank Transaction")


# Internal
def add_transactions(
    result, settings, sync_id, bank, acc_bank, trigger,
    account, bank_account, status, transactions,
    date_from, date_to
):
    log_info((
        "Saving the {0} transactions for bank account \"{1}\"."
    ).format(status, account))
    log_info(transactions)
    
    if not isinstance(transactions, list):
        log_error((
            "The {0} transactions for bank account \"{1}\" are invalid."
        ).format(status, account))
        return 0
    
    if not len(transactions):
        log_error((
            "The {0} transactions for bank account \"{1}\" are empty."
        ).format(status, account))
        return 0
    
    result.synced = True
    for i in range(len(transactions)):
        new_bank_transaction(
            result, settings, acc_bank, account, bank_account,
            transactions.pop(0), status
        )


# Internal
def new_bank_transaction(
    result, settings, acc_bank, account, bank_account, data, status
):
    if "transaction_id" not in data:
        if settings.only_sync_transactions_with_id:
            log_info(_(
                "The new {0} transaction for bank account \"{1}\" has been ignored " +
                "since it has no transaction id."
            ).format(status, account))
            log_info(data)
            return 0
        else:
            data["transaction_id"] = uuid.UUID(hashlib.sha256(
                to_json(data, "").encode("utf-8")
            ).hexdigest()[::2])
    
    if "date" not in data:
        if not settings.ignore_transactions_without_date:
            error(_(
                "The new {0} transaction for bank account \"{1}\" has no date."
            ).format(status, account), False, "VJ27pJA9C9")
        log_info(_(
            "The new {0} transaction for bank account \"{1}\" has been ignored "
            + "since it has no date."
        ).format(status, account))
        log_info(data)
        return 0
    
    if "amount" not in data:
        if not settings.ignore_transactions_without_amount:
            error(_(
                "The new {0} transaction for bank account \"{1}\" has no amount value."
            ).format(status, account), False, "W2tRRL4tee")
        log_info(_(
            "The new {0} transaction for bank account \"{1}\" has been ignored "
            + "since it has no amount."
        ).format(status, account))
        log_info(data)
        return 0
    
    if "currency" not in data:
        if not settings.ignore_transactions_without_currency:
            error(_(
                "The new {0} transaction for bank account \"{1}\" "
                + "has no currency value."
            ).format(status, account), False, "CgKpu46h6g")
        log_info(_(
            "The new {0} transaction for bank account \"{1}\" has been ignored "
            + "since it has no currency."
        ).format(status, account))
        log_info(data)
        return 0
    
    if not frappe.db.exists("Currency", data["currency"]):
        if not settings.ignore_transactions_without_existing_currency:
            error(_(
                "The new {0} transaction currency ({1}) "
                + "for bank account \"{2}\" does not exist."
            ).format(status, data["currency"], account), False, "G2SLqkm9Kw")
        log_info(_(
            "The new {0} transaction for bank account \"{1}\" has been ignored " +
            "since it has no existing currency."
        ).format(status, account))
        log_info(data)
        return 0
    
    if not frappe.db.exists("Currency", {
        "currency_name": data["currency"],
        "enabled": 1
    }):
        if settings.ignore_transactions_without_enabled_currency:
            return 0
    
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
            
            handle_transaction_supplier(settings, entry_data, acc_bank, data)
            handle_transaction_customer(settings, entry_data, acc_bank, data)
            
            doc = (frappe.new_doc(dt)
                .update(entry_data)
                .insert(ignore_permissions=True, ignore_mandatory=True)
                .submit())
            
            result.entries.append(doc.name)
        except Exception as exc:
            log_error(exc)
            error(_(
                "Unable to add new {} transaction for {} bank account."
            ).format(status, account), False, "9HS6PbCfLs")


# Internal
def handle_transaction_supplier(settings, entry, acc_bank, data):
    if (
        settings.add_supplier_info_if_available and
        "supplier" in data and data["supplier"] and
        "name" in data["supplier"]
    ):
        dt = "Supplier"
        name = data["supplier"]["name"]
        ignore_supplier = False
        if not frappe.db.exists(dt, {"supplier_name": name}):
            if (
                settings.create_supplier_if_does_not_exist and
                settings.supplier_default_group
            ):
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
                    log_error(exc)
                    error(_("Unable to create new supplier {0}.").format(name), False, "hJgm52TTpt")
                    ignore_supplier = True
            else:
                log_info(_("The supplier {0} has been ignored.").format(name))
                ignore_supplier = True
                
        else:
            entry.party_type = dt
            entry.party = frappe.db.get_value(dt, {"supplier_name": name}, "name")
            if isinstance(entry.party, list):
                entry.party = entry.party.pop()
        
        if not ignore_supplier:
            if "account" in data["supplier"] and data["supplier"]["account"]:
                if (acc_name := add_party_bank_account(
                    name, dt, acc_bank, data["supplier"]["account"],
                    settings.create_supplier_bank_account_if_does_not_exist
                )):
                    if entry.party:
                        frappe.db.set_value(
                            dt,
                            entry.party,
                            "default_bank_account",
                            acc_name
                        )
                        clear_doc_cache(dt)


# Internal
def handle_transaction_customer(settings, entry, acc_bank, data):
    if (
        not entry.party_type and not entry.party and
        settings.add_customer_info_if_available and
        "customer" in data and data["customer"] and
        "name" in data["customer"]
    ):
        dt = "Customer"
        name = data["customer"]["name"]
        ignore_customer = False
        if not frappe.db.exists(dt, {"customer_name": name}):
            if (
                settings.create_customer_if_does_not_exist and
                settings.customer_default_group and
                settings.customer_default_territory
            ):
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
                    log_error(exc)
                    error(_("Unable to create new customer {}.").format(name), False, "e36EQ2fnAL")
                    ignore_customer = True
            else:
                error(_("The customer {0} has been ignored.").format(name), code="AG4TzU5bzz")
                ignore_customer = True
        else:
            entry.party_type = dt
            entry.party = frappe.db.get_value(dt, {"customer_name": name}, "name")
            if isinstance(entry.party, list):
                entry.party = entry.party.pop()
        
        if not ignore_customer:
            if "account" in data["customer"] and data["customer"]["account"]:
                if (acc_name := add_party_bank_account(
                    name, dt, acc_bank, data["customer"]["account"],
                    settings.create_customer_bank_account_if_does_not_exist
                )):
                    if entry.party:
                        frappe.db.set_value(
                            dt,
                            entry.party,
                            "default_bank_account",
                            acc_name
                        )
                        clear_doc_cache(dt)


# Internal
def add_party_bank_account(party, party_type, acc_bank, account, create_if_not_exist):
    dt = "Bank Account"
    bank_acc_name = make_bank_account_name(party, acc_bank)
    
    iban = account
    if iban and not is_valid_IBAN(iban):
        iban = ""
    
    if not frappe.db.exists(dt, bank_acc_name):
        if create_if_not_exist:
            try:
                (frappe.new_doc(dt)
                    .update({
                        "account_name": party,
                        "bank": acc_bank,
                        "iban": iban,
                        "party_type": party_type,
                        "party": party,
                    })
                    .insert(ignore_permissions=True, ignore_mandatory=True))
                return bank_acc_name
            except Exception as exc:
                log_error(exc)
                error(_(
                    "Unable to create new party bank account {}."
                ).format(bank_acc_name), False, "hCkgTvEW5f")
    else:
        try:
            frappe.db.set_value(dt, bank_acc_name, {
                "iban": iban,
                "party_type": party_type,
                "party": party,
            })
            return bank_acc_name
        except Exception as exc:
            log_error(exc)
            error(_(
                "Unable to update party bank account {}."
            ).format(bank_acc_name), False, "Fj5qbnFW2B")
    
    clear_doc_cache(dt)


# Internal
def is_valid_IBAN(value):
    def encode_char(c):
        return str(9 + ord(c) - 64)
    
    iban = "".join(value.split(" ")).upper()
    flipped = iban[4:] + iban[:4]
    encoded = [encode_char(c) if ord(c) >= 65 and ord(c) <= 90 else c for c in flipped]
    
    try:
        to_check = int("".join(encoded))
    except ValueError:
        return False
    
    if to_check % 97 != 1:
        return False
    
    return True