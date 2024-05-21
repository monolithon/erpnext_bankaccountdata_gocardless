# ERPNext Gocardless Bank © 2024
# Author:  Ameen Ahmed
# Company: Level Up Marketing & Software Development Services
# Licence: Please refer to LICENSE file


import frappe
from frappe import _


# [G Bank Form]
@frappe.whitelist(methods=["POST"])
def store_bank_account(name, account):
    if (
        not name or not isinstance(name, str) or
        not account or not isinstance(account, str)
    ):
        _emit_error({
            "any": 1,
            "error": _("Arguments passed are invalid.")
        })
        return 0
    
    from .cache import get_cached_doc
    
    doc = get_cached_doc("Gocardless Bank", name)
    if not doc:
        _emit_error({
            "name": name,
            "error": _("Gocardless bank \"{0}\" doesn't exist.").format(name)
        })
        return 0
    
    data = None
    for v in doc.bank_accounts:
        if v.account == account and not v.get("bank_account", ""):
            data = {
                "account": v.account,
                "account_id": v.account_id,
                "account_type": v.account_type,
                "account_no": v.account_no,
                "iban": v.iban,
                "is_default": 0
            }
            break
    
    if not data:
        _emit_error({
            "name": name,
            "error": _("Bank account \"{0}\" is not part of Gocardless bank \"{1}\".").format(account, name),
        })
        return 0
    
    if not frappe.db.exists("Bank Account", {
        "bank": doc.bank,
        "company": doc.company,
        "is_default": 1
    }):
        data["is_default"] = 1
    
    return add_bank_account(doc.name, doc.company, doc.bank, data)


# [G Bank Form]
@frappe.whitelist(methods=["POST"])
def change_bank_account(name, account, bank_account):
    if (
        not name or not isinstance(name, str) or
        not account or not isinstance(account, str) or
        not bank_account or not isinstance(bank_account, str)
    ):
        _emit_error({
            "any": 1,
            "error": _("Arguments passed are invalid.")
        })
        return 0
    
    from .cache import get_cached_doc
    
    doc = get_cached_doc("Gocardless Bank", name)
    if not doc:
        _emit_error({
            "name": name,
            "error": _("Gocardless bank \"{0}\" doesn't exist.").format(name)
        })
        return 0
    
    data = None
    for v in doc.bank_accounts:
        if v.account == account and not v.get("bank_account", ""):
            data = v.account
            break
    
    if not data:
        _emit_error({
            "name": name,
            "error": _("Bank account \"{0}\" is not part of Gocardless bank \"{1}\".").format(account, name),
        })
        return 0
    
    return update_bank_account(doc, bank_account, data)


# [G Bank Form]
@frappe.whitelist()
def get_bank_accounts_list():
    dt = "Bank Account"
    data = frappe.get_all(
        dt,
        fields=["name", "account_name"],
        filters=[[dt, "docstatus", "!=", 2]],
        ignore_permissions=True,
        strict=False
    )
    if not data or not isinstance(data, list):
        data = []
    
    return data


# [*Bank Account Form]
@frappe.whitelist(methods=["POST"])
def get_bank_account_data(account):
    if not account or not isinstance(account, str):
        return {"error": _("Arguments required to get bank account data are invalid.")}
    
    from .system import is_enabled
    
    if not is_enabled():
        from .system import app_disabled_message
        
        return {"error": app_disabled_message()}
    
    pdt = "Gocardless Bank"
    pdoc = frappe.qb.DocType(pdt)
    doc = frappe.qb.DocType(f"{pdt} Account")
    data = (
        frappe.qb.from_(doc)
        .select(
            doc.parent,
            pdoc.company,
            doc.account,
            doc.status,
            doc.last_sync
        )
        .inner_join(pdoc)
        .on(pdoc.name == doc.parent)
        .where(doc.parenttype == pdt)
        .where(doc.parentfield == "bank_accounts")
        .where(doc.bank_account == account)
        .where(pdoc.disabled == 0)
        .limit(1)
    ).run(as_dict=True)
    if not data or not isinstance(data, list):
        return {"error": _("Bank account \"{0}\" is disabled or doesn't exist.").format(account)}
    
    data = data.pop(0)
    ret = {
        "bank_account": account,
        "status": data["status"]
    }
    if data["status"] == "Ready":
        ret.update({
            "bank": data["parent"],
            "company": data["company"],
            "account": data["account"],
            "last_sync": data["last_sync"]
        })
    
    return ret


# [Bank]*
def get_client_bank_accounts(company, bank, auth_id, publish=False):
    from .system import get_client
    
    client = get_client(company)
    if isinstance(client, dict):
        _store_error({
            "error": "Unable to get bank accounts list from api since app is disabled.",
            "bank": bank,
            "data": client
        })
        if publish:
            _emit_error({"bank": bank, "error": client["error"]})
        
        return 0
    
    accounts = client.get_accounts(auth_id)
    if "error" in accounts:
        if publish:
            _emit_error({
                "bank": bank,
                "error": _("Unable to get bank accounts list from api.")
            })
        
        return 0
    
    data = []
    for v in accounts:
        va = client.get_account_data(v)
        if not va or "error" in va:
            _store_error({
                "error": "Bank account data received is empty or invalid.",
                "bank": bank,
                "account": v
            })
            continue
            
        vb = client.get_account_balances(v)
        if not vb or "error" in vb:
            _store_error({
                "error": "Bank account balances received is empty or invalid.",
                "bank": bank,
                "account": v
            })
            continue
        
        vd = client.get_account_details(v)
        if not vd or "error" in vd:
            _store_error({
                "error": "Bank account details received is empty or invalid.",
                "bank": bank,
                "account": v
            })
            continue
        
        from .common import to_json
        
        v = {"id": v}
        v.update(va)
        v.update({"balances": to_json(vb)})
        v.update(vd)
        data.append(v)
    
    if data:
        data = prepare_bank_accounts(data, bank, company)
    
    return data


# [Internal]
def prepare_bank_accounts(accounts, bank, company):
    from .system import settings
    from .company import get_company_currency
    from .currency import get_currencies
    
    doc = settings()
    currency = get_company_currency(company)
    currencies = {
        "list": get_currencies(),
        "new": [],
        "enable": [],
    }
    exist = []
    idx = 1
    result = []
    
    for v in accounts:
        if "name" not in v:
            v["name"] = f"{bank} Account"
        if "currency" not in v:
            if not currency or doc.bank_account_without_currency == "Ignore":
                continue
            v["currency"] = currency
        if v["currency"] not in currencies["list"]:
            if doc.bank_account_currency_doesnt_exist == "Ignore":
                continue
            currencies["new"].append(v["currency"])
        elif not currencies["list"][v["currency"]]:
            if doc.bank_account_currency_disabled == "Ignore":
                continue
            currencies["enable"].append(v["currency"])
        
        ret = gen_account_name(v, exist, idx)
        if not ret:
            _store_error({
                "error": "Unable to get bank account name.",
                "bank": bank,
                "company": company,
                "data": v
            })
            continue
        
        v["name"] = ret[0]
        idx = ret[1]
        iban = v.get("iban", "")
        if iban and not is_valid_IBAN(iban):
            v["iban"] = ""
        
        result.append({
            "account": v["name"],
            "account_id": v["id"],
            "account_type": v.get("cashAccountType", ""),
            "account_no": v.get("resourceId", ""),
            "account_currency": v["currency"],
            "iban": v.get("iban", ""),
            "balances": v["balances"],
            "status": v["status"],
            "bank_account": "",
        })
    
    if currencies["new"]:
        from .currency import enqueue_add_currencies
        
        enqueue_add_currencies(bank, currencies["new"])
    
    if currencies["enable"]:
        from .currency import enqueue_enable_currencies
        
        enqueue_enable_currencies(bank, currencies["enable"])
    
    return result


# [Internal]
def gen_account_name(data: dict, exist: list, idx: int):
    name = [data["name"], str(data["currency"]).upper()]
    tmp = " - ".join(name)
    if tmp not in exist:
        exist.append(tmp)
        return [tmp, idx]
    
    for i in range(idx, idx + 10):
        name.append(idx)
        idx += 1
        tmp = " - ".join(name)
        if tmp not in exist:
            exist.append(tmp)
            return [tmp, idx]
    
    return None


# [Bank]*
def store_bank_accounts(name, accounts):
    from .cache import get_cached_doc
    
    doc = get_cached_doc("Gocardless Bank", name)
    if not doc:
        return []
    
    existing = {v.account:v for v in doc.bank_accounts}
    for v in accounts:
        if v["account"] not in existing:
            data = v
        else:
            data = existing[v["account"]]
            doc.bank_accounts.remove(data)
            data["status"] = v["status"]
        
        doc.append("bank_accounts", data)
    
    doc.save(ignore_permissions=True)
    
    from .realtime import emit_reload_bank_accounts
    
    emit_reload_bank_accounts({"name": doc.name, "bank": doc.bank})


# [Internal]
def add_bank_account(name, company, bank, data):
    if data["account_type"]:
        from .bank_account_type import add_account_type
        
        ret = add_account_type(data["account_type"])
        if not ret:
            _emit_error({
                "name": name,
                "error": _("Unable to create bank account type \"{0}\" for bank account \"{1}\".").format(data["account_type"], data["account"])
            })
            return 0
    
    err = None
    dt = "Bank Account"
    account_name = "{0} - {1}".format(data["account"], bank)
    account = {
        "account_name": data["account"],
        "bank": bank,
        "account_type": data["account_type"],
        "gocardless_bank_account_no": data["account_no"],
        "company": company,
        "iban": data["iban"],
        "is_default": data["is_default"],
        "from_gocardless": 1
    }
    if not frappe.db.exists(dt, account_name):
        try:
            (frappe.new_doc(dt)
                .update(account)
                .insert(ignore_permissions=True, ignore_mandatory=True))
        except frappe.UniqueValidationError:
            err = _("Bank account \"{0}\" already exists.").format(data["account"])
        except Exception as exc:
            err = _("Unable to create bank account \"{0}\" of Gocardless bank \"{1}\".").format(data["account"], bank)
            _store_error({
                "error": "Unable to create bank account.",
                "gc_bank": name,
                "bank": bank,
                "company": company,
                "data": data,
                "exception": str(exc)
            })
    
    else:
        try:
            (frappe.get_doc(dt, account_name)
                .update(account)
                .save(ignore_permissions=True))
        except Exception as exc:
            err = _("Unable to update bank account \"{0}\" of Gocardless bank \"{1}\".").format(data["account"], bank)
            _store_error({
                "error": "Unable to create bank account.",
                "gc_bank": name,
                "bank": bank,
                "company": company,
                "data": data,
                "exception": str(exc)
            })
    
    if not err:
        from .cache import clear_doc_cache
        
        clear_doc_cache(dt)
        ret = update_bank_account(name, account_name, data["account"])
        if not ret:
            err = _("Unable to update Gocardless bank account \"{0}\" of Gocardless bank \"{1}\".").format(data["account"], bank)
    
    if err:
        from .common import log_error
        
        log_error(err)
        _emit_error({"name": name, "error": err})
        return 0
    
    return 1


# [Internal]
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


# [Internal]
def update_bank_account(name, bank_account, account):
    if not isinstance(name, str):
        doc = name
    else:
        from .cache import get_cached_doc
        
        doc = get_cached_doc("Gocardless Bank", name)
        if not doc:
            return 0
    
    for v in doc.bank_accounts:
        if v.account == account and not v.get("bank_account", ""):
            v.update({"bank_account": bank_account})
            doc.save(ignore_permissions=True)
            return 1
    
    if not isinstance(name, str):
        _emit_error({
            "name": doc.name,
            "error": _("Bank account \"{0}\" is not part of Gocardless bank \"{1}\".").format(account, doc.name),
        })
    
    return 0


# [Bank Transaction, Schedule]
def update_bank_account_data(name, data):
    frappe.db.set_value(
        "Gocardless Bank Account",
        name,
        data,
        update_modified=False
    )


# [Bank Transaction]
def add_party_bank_account(party, party_type, account_bank, account):
    dt = "Bank Account"
    bank_acc_name = "{0} - {1}".format(party, account_bank)
    iban = account
    if iban and not is_valid_IBAN(iban):
        iban = ""
    
    if not frappe.db.exists(dt, bank_acc_name):
        try:
            (frappe.new_doc(dt)
                .update({
                    "account_name": party,
                    "bank": account_bank,
                    "iban": iban,
                    "party_type": party_type,
                    "party": party,
                    "from_gocardless": 1
                })
                .insert(ignore_permissions=True, ignore_mandatory=True))
            
            from .cache import clear_doc_cache
    
            clear_doc_cache(dt)
            return bank_acc_name
        except Exception as exc:
            _store_error({
                "error": "Unable to create party bank account.",
                "party": party,
                "party_type": party_type,
                "account_bank": account_bank,
                "account": account,
                "exception": str(exc)
            })
    else:
        try:
            frappe.db.set_value(dt, bank_acc_name, {
                "iban": iban,
                "party_type": party_type,
                "party": party,
            })
            
            from .cache import clear_doc_cache
    
            clear_doc_cache(dt)
            return bank_acc_name
        except Exception as exc:
            _store_error({
                "error": "Unable to update party bank account.",
                "party": party,
                "party_type": party_type,
                "account_bank": account_bank,
                "account": account,
                "exception": str(exc)
            })
    
    return 0


# [Internal]
def _store_error(data):
    from .common import store_error
    
    store_error(data)


# [Internal]
def _emit_error(data):
    from .realtime import emit_bank_error
    
    emit_bank_error(data)