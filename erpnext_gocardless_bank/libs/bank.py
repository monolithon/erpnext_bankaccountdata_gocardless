# Expenses © 2024
# Author:  Ameen Ahmed
# Company: Level Up Marketing & Software Development Services
# Licence: Please refer to LICENSE file


import frappe
from frappe import _


# [G Bank Form]
@frappe.whitelist()
def get_banks(company):
    if not company or not isinstance(company, str):
        return {"error": _("Arguments required to load supported banks is invalid.")}
    
    return get_banks_list(company, False)


# [G Bank, Internal]
def get_banks_list(company: str, raw=True):
    from .company import get_company_country_name
    
    country = get_company_country_name(company)
    if not country:
        if raw:
            return None
        
        return {"error": _("Company \"{0}\" doesn't have a valid country.").format(company)}
    
    from .country import get_country_code
    
    code = get_country_code(country)
    if not code:
        if raw:
            return None
        
        return {"error": _("Country \"{0}\" doesn't exist.").format(country)}
    
    from .cache import get_cache
    
    dt = "Gocardless"
    key = f"banks-list-{code}"
    data = get_cache(dt, key, True)
    if not isinstance(data, list):
        from .system import get_client
        
        client = get_client(company)
        if isinstance(client, dict):
            if raw:
                return None
            
            return client
        
        data = client.get_banks(code)
    
    if data and isinstance(data, list):
        from .cache import set_cache
        
        set_cache(dt, key, data, 7 * 24 * 60 * 60)
    
    if raw and (not data or not isinstance(data, list)):
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
    if doc._is_draft:
        return {"error": _("Bank \"{0}\" can't be authorized before being submitted.").format(name)}
    if doc._is_cancelled:
        return {"error": _("Bank \"{0}\" can't be authorized after being cancelled.").format(name)}
    if doc.bank != bank or doc.bank_id != bank_id:
        return {"error": _("Authorization data for bank \"{0}\" is invalid.").format(name)}
    
    doc.auth_id = auth_id
    doc.auth_expiry = auth_expiry
    doc.auth_status = "Linked"
    doc.save(ignore_permissions=True)
    return 1


# [G Bank]
def enqueue_sync_bank(name, bank, company, auth_id):
    from .background import is_job_running
    
    job_id = f"gocardless-sync-bank-{name}"
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


# [G Bank]
def dequeue_jobs(name, accounts):
    from .background import dequeue_job
    
    dequeue_job(f"gocardless-sync-bank-{name}")
    for account in accounts:
        dequeue_job(f"gocardless-bank-transactions-sync-{account}")


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
    
    if not status:
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
        from .common import store_error
        
        store_error({
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
def _emit_error(data):
    from .realtime import emit_bank_error
    
    emit_bank_error(data)


# [Internal]
def _emit_reload(data):
    from .realtime import emit_reload_bank_accounts
    
    emit_reload_bank_accounts(data)