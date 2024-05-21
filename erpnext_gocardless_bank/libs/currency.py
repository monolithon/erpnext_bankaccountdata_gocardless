# ERPNext Gocardless Bank © 2024
# Author:  Ameen Ahmed
# Company: Level Up Marketing & Software Development Services
# Licence: Please refer to LICENSE file


import frappe


# [Bank]
def get_currencies_status():
    from .cache import get_cache
    
    dt = "Currency"
    key = "currencies-list-status"
    data = get_cache(dt, key, True)
    if isinstance(data, dict):
        return data
    
    data = frappe.get_all(
        dt,
        fields=["name", "enabled"],
        ignore_permissions=True,
        strict=False
    )
    if not data or not isinstance(data, list):
        data = {}
    else:
        from frappe.utils import cint
        
        data = {v["name"]:cint(v["enabled"]) for v in data}
    
    from .cache import set_cache
    
    set_cache(dt, key, data, 15 * 60)
    return data


# [Bank]
def enqueue_add_currencies(bank, names):
    from .background import is_job_running
    
    job_id = f"gocardless-add-currencies-{bank}"
    if not is_job_running(job_id):
        from .background import enqueue_job
        
        enqueue_job(
            "erpnext_gocardless_bank.libs.currency.add_currencies",
            job_id,
            names=names
        )


# [Bank Transaction]
def get_currency_status(name):
    data = get_currencies_status()
    return data.get(name, None)


# [Bank Transaction, Internal]
def add_currencies(names):
    dt = "Currency"
    cnt = 0
    for name in list(set(names)):
        try:
            (frappe.new_doc(dt)
                .update({
                    "currency_name": name,
                    "enabled": 1,
                    "from_gocardless": 1
                })
                .insert(ignore_permissions=True, ignore_mandatory=True))
            
            cnt += 1
        except Exception as exc:
            from .common import store_error
            
            store_error({
                "error": "Unable to add currency.",
                "name": name,
                "exception": str(exc)
            })
    
    if cnt:
        from .cache import clear_doc_cache
    
        clear_doc_cache(dt)


# [Bank]
def enqueue_enable_currencies(bank, names):
    from .background import is_job_running
    
    job_id = f"gocardless-enable-currencies-{bank}"
    if not is_job_running(job_id):
        from .background import enqueue_job
        
        enqueue_job(
            "erpnext_gocardless_bank.libs.currency.enable_currencies",
            job_id,
            names=names
        )


# [Internal]
def enable_currencies(names):
    dt = "Currency"
    cnt = 0
    for name in list(set(names)):
        try:
            frappe.db.set_value(dt, name, "enabled", 1)
            cnt += 1
        except Exception as exc:
            from .common import store_error
            
            store_error({
                "error": "Unable to up currency.",
                "name": name,
                "exception": str(exc)
            })
    
    if cnt:
        from .cache import clear_doc_cache
    
        clear_doc_cache(dt)