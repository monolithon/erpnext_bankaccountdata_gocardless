# Expenses © 2024
# Author:  Ameen Ahmed
# Company: Level Up Marketing & Software Development Services
# Licence: Please refer to LICENSE file


import frappe
from frappe import _


# [G Bank, G Bank Form]
@frappe.whitelist()
def get_banks(company, country=None, pay_option=0, raw=False):
    if (
        not company or not isinstance(company, str) or
        (country and not isinstance(country, str)) or
        (pay_option and not isinstance(pay_option, int))
    ):
        return {"error": _("Arguments required to load supported banks is invalid.")}
    
    if not country:
        from .company import get_company_country
        
        country = get_company_country(company)
        if not country:
            return {"error": _("Company \"{0}\" doesn't have a valid country.").format(company)}
    
    if len(country) > 2:
        from .country import get_country_code
        
        code = get_country_code(country)
        if not code:
            return {"error": _("Country \"{0}\" doesn't exist.").format(country)}
        
        country = code.upper()
    else:
        from .country import country_code_exists
        
        if not country_code_exists(country):
            return {"error": _("Country code \"{0}\" doesn't exist.").format(country)}
        
        country = country.upper()
    
    from .cache import get_cache
    
    dt = "Gocardless"
    key = f"banks-list-{country}"
    if pay_option:
        key = f"{key}-pay"
    
    data = get_cache(dt, key, True)
    if not isinstance(data, list):
        from .system import get_client
        
        client = get_client(company)
        if isinstance(client, dict):
            return client
        
        data = client.get_banks(country, 1 if pay_option else 0)
    
    if data and isinstance(data, list):
        from .cache import set_cache
        
        set_cache(dt, key, data, 2 * 24 * 60 * 60)
    
    if raw and not isinstance(data, list):
        return None
    
    return data


# [G JS]
@frappe.whitelist(methods=["POST"])
def get_bank_auth(name, ref_id, company, bank, bank_id, transaction_days=0):
    if (
        not name or not isinstance(name, str) or
        not ref_id or not isinstance(ref_id, str) or
        not company or not isinstance(company, str) or
        not bank or not isinstance(bank, str) or
        not bank_id or not isinstance(bank_id, str)
    ):
        _store_error({
            "error": "Invalid bank link data args",
            "name": name,
            "ref_id": ref_id,
            "company": company,
            "bank": bank,
            "bank_id": bank_id,
            "transaction_days": transaction_days
        })
        return {"error": _("Arguments required to get bank link data is invalid.")}
    
    from .system import get_client
    
    client = get_client(company)
    if isinstance(client, dict):
        return client
    
    return client.get_bank_link(name, ref_id, bank, bank_id, transaction_days)


# [G JS]
@frappe.whitelist(methods=["POST"])
def save_bank_auth(name, bank, bank_id, auth_id, auth_expiry):
    if (
        not name or not isinstance(name, str) or
        not bank or not isinstance(bank, str) or
        not bank_id or not isinstance(bank_id, str) or
        not auth_id or not isinstance(auth_id, str) or
        not auth_expiry or not isinstance(auth_expiry, str)
    ):
        return {"error": _("Arguments required for saving bank authorization are invalid.")}
    
    doc = get_bank_doc(name)
    if not doc:
        return {"error": _("Bank \"{0}\" doesn't exist.").format(name)}
    if not doc._is_submitted:
        return {"error": _("Bank \"{0}\" can't be authorized before being submitted.").format(name)}
    if doc.bank != bank or doc.bank_id != bank_id:
        return {"error": _("Authorization data for \"{0}\" is invalid.").format(name)}
    
    doc.auth_id = auth_id
    doc.auth_expiry = auth_expiry
    doc.auth_status = "Linked"
    doc.save(ignore_permissions=True)
    return 1


# [G Bank]
def enqueue_sync_bank(name, bank, company, auth_id):
    from .background import is_job_running
    
    job_id = f"gocardless-sync-bank-{bank}"
    if not is_job_running(job_id):
        from .background import enqueue_job
        
        enqueue_job(
            "erpnext_gocardless_bank.libs.bank.sync_bank",
            job_id,
            timeout=30000,
            name=name,
            bank=bank,
            company=company,
            auth_id=auth_id
        )


# [Internal]*
def sync_bank(name, bank, company, auth_id):
    from .bank_account import get_client_bank_accounts
    
    status = 0
    accounts = get_client_bank_accounts(company, bank, auth_id)
    if accounts:
        from .bank_account import store_bank_accounts
        
        status = store_bank_accounts(get_bank_doc(name), accounts)
        if status:
            _emit_reload({
                "name": name,
                "bank": bank
            })
        else:
            _emit_error({
                "name": name,
                "bank": bank,
                "error": _("Unable to sync bank accounts of bank \"{0}\".").format(name)
            })
    
    return status


# [G Bank]
def add_bank(bank: str):
    dt = "Bank"
    if frappe.db.exists(dt, bank):
        return bank
    
    try:
        (frappe.new_doc(dt)
            .update({
                "bank_name": bank,
                "from_gocardless": 1
            })
            .insert(ignore_permissions=True, ignore_mandatory=True))
        
        from .cache import clear_doc_cache
        
        clear_doc_cache(dt)
        return bank
    except Exception as exc:
        _store_error({
            "error": "Unable to add bank to ERPNext.",
            "bank": bank,
            "exception": str(exc)
        })
        return None


# [G Bank]
def remove_bank_auth(company, auth_id):
    from .system import get_client
    
    client = get_client(company)
    if not isinstance(client, dict):
        client.remove_bank_link(auth_id)


# [Bank Account, Bank Transaction, Internal]
def get_bank_doc(name):
    from .cache import get_cached_doc
    
    return get_cached_doc("Gocardless Bank", name)


# [Internal]
def _store_error(data):
    from .common import store_error
    
    store_error(data)


# [Internal]
def _emit_error(data):
    from .realtime import emit_bank_error
    
    emit_bank_error(data)


# [Internal]
def _emit_reload(data):
    from .realtime import emit_reload_bank_accounts
    
    emit_reload_bank_accounts(data)