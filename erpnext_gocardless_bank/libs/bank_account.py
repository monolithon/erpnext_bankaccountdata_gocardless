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
    
    from .bank import get_bank_doc
    
    doc = get_bank_doc(name)
    if not doc:
        _emit_error({
            "name": name,
            "error": _("Gocardless bank \"{0}\" doesn't exist.").format(name)
        })
        return 0
    
    row = None
    data = None
    for v in doc.bank_accounts:
        if v.account == account and not v.get("bank_account_ref", ""):
            row = v
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
        "bank": doc.bank_ref,
        "company": doc.company,
        "is_default": 1
    }):
        data["is_default"] = 1
    
    update = 0
    if data["account_type"]:
        from .bank_account_type import add_account_type
        
        account_type = add_account_type(data["account_type"])
        if not account_type:
            _emit_error({
                "name": name,
                "error": _("ERPNext: Unable to create bank account type \"{0}\" for bank account \"{1}\".").format(data["account_type"], data["account"])
            })
            return 0
        
        if not row.bank_account_type_ref:
            update = 1
            row.bank_account_type_ref = account_type
            data["account_type"] = account_type
    
    from .currency import get_currency_status
    
    currency_status = get_currency_status(row.account_currency)
    if currency_status is None:
        from .currency import enqueue_add_currencies
        
        enqueue_add_currencies([row.account_currency])
    elif not currency_status:
        from .currency import enqueue_enable_currencies
        
        enqueue_enable_currencies([row.account_currency])
    
    bank_account = add_bank_account(doc, data)
    if bank_account and not row.bank_account_ref:
        row.bank_account_ref = bank_account
        update = 1
    
    if update:
        doc.save(ignore_permissions=True)
    
    return 1 if bank_account else 0


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
    
    from .bank import get_bank_doc
    
    doc = get_bank_doc(name)
    if not doc:
        _emit_error({
            "name": name,
            "error": _("Gocardless bank \"{0}\" doesn't exist.").format(name)
        })
        return 0
    
    data = None
    for v in doc.bank_accounts:
        if v.account == account and not v.get("bank_account_ref", ""):
            data = v.account
            break
    
    if not data:
        _emit_error({
            "name": name,
            "error": _("Bank account \"{0}\" is not part of Gocardless bank \"{1}\".").format(account, name),
        })
        return 0
    
    return update_bank_account(doc, bank_account, data, True)


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
            doc.bank_account_ref,
            doc.status,
            doc.last_sync
        )
        .inner_join(pdoc)
        .on(pdoc.name == doc.parent)
        .where(doc.parenttype == pdt)
        .where(doc.parentfield == "bank_accounts")
        .where(doc.bank_account_ref == account)
        .where(pdoc.disabled == 0)
        .limit(1)
    ).run(as_dict=True)
    if not data or not isinstance(data, list):
        return {"error": _("Bank account \"{0}\" is disabled or doesn't exist.").format(account)}
    
    data = data.pop(0)
    ret = {
        "bank_account": data["bank_account_ref"],
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
def get_client_bank_accounts(company, bank, auth_id):
    from .system import get_client
    
    client = get_client(company)
    if isinstance(client, dict):
        _store_error({
            "error": "Unable to get bank accounts list from api since app is disabled.",
            "bank": bank,
            "data": client
        })
        return 0
    
    accounts = client.get_accounts(auth_id)
    if "error" in accounts:
        _store_error({
            "error": "Unable to get bank accounts list from api.",
            "bank": bank,
            "data": accounts
        })
        return 0
    
    data = []
    for i in range(len(accounts)):
        v = accounts.pop(0)
        va = client.get_account_data(v)
        if not va or "error" in va:
            _store_error({
                "error": "Bank account data received is empty or invalid.",
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
        
        vb = client.get_account_balances(v)
        if not vb or "error" in vb:
            _store_error({
                "error": "Bank account balances received is empty or invalid.",
                "bank": bank,
                "account": v
            })
            continue
        
        from .common import to_json
        
        v = {"id": v, "balances": to_json(vb)}
        v.update(va)
        v.update(vd)
        data.append(v)
    
    if data:
        data = prepare_bank_accounts(data, bank, company)
    
    return data if data else 0


# [Internal]
def prepare_bank_accounts(accounts, bank, company):
    from .system import settings
    from .company import get_company_currency
    from .currency import get_currencies_status
    
    doc = settings()
    currency = get_company_currency(company)
    currencies = get_currencies_status()
    skip = "Ignore"
    exist = []
    idx = 1
    result = []
    
    for i in range(len(accounts)):
        v = accounts.pop(0)
        if "name" not in v:
            v["name"] = f"{bank} Account"
        if "currency" not in v:
            if not currency or doc.bank_account_without_currency == skip:
                continue
            v["currency"] = currency
        if v["currency"] not in currencies:
            if doc.bank_account_currency_doesnt_exist == skip:
                continue
        elif not currencies[v["currency"]]:
            if doc.bank_account_currency_disabled == skip:
                continue
        
        ret = make_account_name(v, exist, idx)
        idx = ret[1]
        if not ret[0]:
            ret = make_account_name(v, exist, idx)
            if not ret[0]:
                _store_error({
                    "error": "Unable to make unique bank account name.",
                    "bank": bank,
                    "company": company,
                    "data": v
                })
                continue
        
        v["name"] = ret[0]
        iban = v.get("iban", "")
        if iban and not is_valid_IBAN(iban):
            v["iban"] = ""
        
        result.append({
            "account": v["name"],
            "account_id": v["id"],
            "account_currency": v["currency"],
            "status": v["status"],
            "account_type": v.get("cashAccountType", ""),
            "account_no": v.get("resourceId", ""),
            "iban": v.get("iban", ""),
            "balances": v["balances"]
        })
    
    return result if result else 0


# [Internal]
def make_account_name(data: dict, exist: list, idx: int):
    name = [data["name"], str(data["currency"]).upper()]
    name = " - ".join(name)
    if name not in exist:
        exist.append(name)
        return [name, idx]
    
    for i in range(10):
        tmp = name + " - #" + str(idx)
        idx += 1
        if tmp not in exist:
            exist.append(tmp)
            return [tmp, idx]
    
    return [None, idx]


# [Bank]*
def store_bank_accounts(doc, accounts):
    if not doc:
        return 0
    
    if doc.bank_accounts:
        existing = {v.account:v for v in doc.bank_accounts}
    else:
        existing = {}
    
    for i in range(len(accounts)):
        v = accounts.pop(0)
        if v["account"] not in existing:
            data = v
        else:
            data = existing.pop(v["account"])
            doc.bank_accounts.remove(data)
            for k in v:
                if k != "account" and v[k] and v[k] != data.get(k, ""):
                    data.set(k, v[k])
        
        doc.append("bank_accounts", data)
    
    doc.save(ignore_permissions=True)
    return 1


# [Internal]
def add_bank_account(doc, data):
    err = None
    dt = "Bank Account"
    account_name = "{0} - {1}".format(data["account"], doc.bank)
    account = {
        "account_name": data["account"],
        "bank": doc.bank,
        "account_type": data["account_type"],
        "gocardless_bank_account_no": data["account_no"],
        "company": doc.company,
        "iban": data["iban"]
    }
    if not frappe.db.exists(dt, account_name):
        try:
            (frappe.new_doc(dt)
                .update(account)
                .update({
                    "is_default": data["is_default"],
                    "from_gocardless": 1
                })
                .insert(ignore_permissions=True, ignore_mandatory=True))
        except frappe.UniqueValidationError:
            err = _("ERPNext: Bank account \"{0}\" of bank \"{1}\" already exists.").format(data["account"], doc.bank)
        except Exception as exc:
            err = _("ERPNext: Unable to create bank account \"{0}\" of bank \"{1}\".").format(data["account"], doc.bank)
            _store_error({
                "error": "Unable to create bank account.",
                "gc_bank": doc.name,
                "bank": doc.bank,
                "company": doc.company,
                "data": data,
                "exception": str(exc)
            })
    
    else:
        try:
            (frappe.get_doc(dt, account_name)
                .update(account)
                .save(ignore_permissions=True))
        except Exception as exc:
            err = _("ERPNext: Unable to update bank account \"{0}\" of bank \"{1}\".").format(data["account"], doc.bank)
            _store_error({
                "error": "Unable to create bank account.",
                "gc_bank": doc.name,
                "bank": doc.bank,
                "company": doc.company,
                "data": data,
                "exception": str(exc)
            })
    
    if not err:
        from .cache import clear_doc_cache
        
        clear_doc_cache(dt)
        ret = update_bank_account(doc, account_name, data["account"])
        if not ret:
            err = _("Unable to update bank account \"{0}\" of bank \"{1}\".").format(data["account"], doc.bank)
    
    if err:
        from .common import log_error
        
        log_error(err)
        _emit_error({"name": doc.name, "error": err})
        return None
    
    return account_name


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
def update_bank_account(doc, bank_account, account, emit=False):
    if not doc:
        return 0
    
    for v in doc.bank_accounts:
        if v.account == account:
            v.update({"bank_account_ref": bank_account})
            doc.save(ignore_permissions=True)
            return 1
    
    if emit:
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