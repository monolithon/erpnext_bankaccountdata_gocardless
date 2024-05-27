# Expenses © 2024
# Author:  Ameen Ahmed
# Company: Level Up Marketing & Software Development Services
# Licence: Please refer to LICENSE file


import frappe
from frappe import _


# [G Bank, G Bank Form]
@frappe.whitelist()
def get_banks(company, country=None, pay_option=0):
    if (
        not company or not isinstance(company, str) or
        (country and not isinstance(country, str)) or
        (pay_option and not isinstance(pay_option, int))
    ):
        return {"error": _("Data required to load Gocardless banks are invalid.")}
    
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
    if isinstance(data, list):
        return data
    
    from .system import get_client
    
    client = get_client(company)
    if isinstance(client, dict):
        return client
    
    data = client.get_banks(country, 1 if pay_option else 0)
    if data and isinstance(data, list):
        from .cache import set_cache
        
        set_cache(dt, key, data, 2 * 24 * 60 * 60)
    
    return data


# [G JS]
@frappe.whitelist(methods=["POST"])
def get_bank_link(company, bank_id, ref_id, transaction_days=0, docname=None):
    if (
        not company or not isinstance(company, str) or
        not bank_id or not isinstance(bank_id, str) or
        not ref_id or not isinstance(ref_id, str) or
        (docname and not isinstance(docname, str))
    ):
        from .common import store_error
        
        store_error({
            "error": "Invalid Gocardless bank link args",
            "company": company,
            "bank_id": bank_id,
            "ref_id": ref_id,
            "transaction_days": transaction_days,
            "docname": docname
        })
        return {"error": _("Data required to get Gocardless bank link are invalid.")}
    
    from .system import get_client
    
    client = get_client(company)
    if isinstance(client, dict):
        return client
    
    return client.get_bank_link(bank_id, ref_id, transaction_days, docname)


# [G Bank List, G Bank Form]
@frappe.whitelist(methods=["POST"])
def save_bank_link(name, auth_id, auth_expiry):
    if (
        not name or not isinstance(name, str) or
        not auth_id or not isinstance(auth_id, str) or
        not auth_expiry or not isinstance(auth_expiry, str)
    ):
        return {"error": _("Data required to save Gocardless bank link are invalid.")}
    
    from .cache import get_cached_doc
    
    doc = get_cached_doc("Gocardless Bank", name)
    if not doc:
        return {"error": _("Gocardless bank \"{0}\" doesn't exist.").format(name)}
    
    is_new = 0
    if not doc.auth_id or not doc.bank_accounts:
        is_new = 1
    
    doc.auth_id = auth_id
    doc.auth_expiry = auth_expiry
    doc.auth_status = "Linked"
    doc.save()
    
    if is_new:
        enqueue_save_bank(doc.name, doc.bank, doc.company, auth_id)
    else:
        enqueue_update_bank(doc.name, doc.bank, doc.company, auth_id)
    
    return 1


# [Internal]
def enqueue_save_bank(name, bank, company, auth_id):
    from .background import is_job_running
    
    job_id = f"gocardless-save-bank-{bank}"
    if not is_job_running(job_id):
        from .background import enqueue_job
        
        enqueue_job(
            "erpnext_gocardless_bank.libs.bank.save_bank",
            job_id,
            name=name,
            bank=bank,
            company=company,
            auth_id=auth_id
        )


# [Internal]
def enqueue_update_bank(name, bank, company, auth_id):
    from .background import is_job_running
    
    job_id = f"gocardless-update-bank-{bank}"
    if not is_job_running(job_id):
        from .background import enqueue_job
        
        enqueue_job(
            "erpnext_gocardless_bank.libs.bank.update_bank",
            job_id,
            name=name,
            bank=bank,
            company=company,
            auth_id=auth_id
        )


# [Internal]*
def save_bank(name, bank, company, auth_id):
    if add_bank(bank):
        from .bank_account import get_client_bank_accounts
        
        accounts = get_client_bank_accounts(company, bank, auth_id)
        if accounts:
            from .bank_account import store_bank_accounts
            
            store_bank_accounts(name, accounts)
        else:
            from .realtime import emit_bank_error
            
            emit_bank_error({
                "name": name,
                "bank": bank,
                "error": _("Unable to create or update bank accounts of {0}.").format(bank)
            })


# [Internal]*
def update_bank(name, bank, company, auth_id):
    from .bank_account import get_client_bank_accounts
    
    accounts = get_client_bank_accounts(company, bank, auth_id, True)
    if accounts:
        from .bank_account import store_bank_accounts
        
        store_bank_accounts(name, accounts)


# [Internal]*
def add_bank(bank: str):
    dt = "Bank"
    if frappe.db.exists(dt, bank):
        return 1
    
    try:
        (frappe.new_doc(dt)
            .update({
                "bank_name": bank,
                "from_gocardless": 1
            })
            .insert(ignore_permissions=True, ignore_mandatory=True))
        
        from .cache import clear_doc_cache
        
        clear_doc_cache(dt)
        return 1
    except Exception as exc:
        from .common import store_error
        from .realtime import emit_bank_error
        
        store_error({
            "error": "Unable to add new bank.",
            "bank": bank,
            "exception": str(exc)
        })
        emit_bank_error({
            "bank": bank,
            "error": _("Unable to add the bank \"{0}\".").format(bank)
        })
        return 0