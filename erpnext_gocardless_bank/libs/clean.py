# Expenses © 2024
# Author:  Ameen Ahmed
# Company: Level Up Marketing & Software Development Services
# Licence: Please refer to LICENSE file


import frappe


# [G Bank]
def enqueue_bank_trash(doc):
    from .background import is_job_running
    
    job_id = f"gocardless-bank-trash-{doc.name}"
    if not is_job_running(job_id):
        from .background import enqueue_job
        
        accounts = [v.bank_account_ref for v in doc.bank_accounts if v.bank_account_ref]
        enqueue_job(
            "erpnext_gocardless_bank.libs.clean.clean_trash",
            job_id,
            queue="long",
            name=doc.name,
            bank=doc.bank_ref,
            company=doc.company,
            accounts=accounts
        )


# [Internal]
def clean_trash(name, bank, company, accounts):
    from .system import settings
    
    doc = settings()
    data = None
    if (
        accounts and (
            doc.clean_currency or
            doc.clean_supplier or
            doc.clean_customer
        )
    ):
        data = get_transactions_data(accounts)
    
    if accounts and doc.clean_bank_transaction:
        clean_bank_transactions(accounts)
    
    if accounts and doc.clean_bank_account:
        clean_bank_accounts(accounts, bank, company)
    
    if bank and doc.clean_bank:
        clean_bank(bank)
    
    if data:
        if doc.clean_currency and data["currency"]:
            clean_currency(data["currency"])
        
        if doc.clean_supplier and data["supplier"]:
            clean_supplier(data["supplier"])
        
        if doc.clean_customer and data["customer"]:
            clean_customer(data["customer"])
    
    clean_sync_log(name)


# [Internal]
def get_transactions_data(accounts):
    dt = "Bank Transaction"
    data = frappe.get_all(
        dt,
        fields=[
            "currency",
            "party_type",
            "party"
        ],
        filters=[
            [dt, "bank_account", "in", accounts],
            [dt, "from_gocardless", "=", 1]
        ],
        ignore_permissions=True,
        strict=False
    )
    if not data or not isinstance(data, list):
        return None
    
    ret = {
        "currency": [],
        "supplier": [],
        "customer": [],
    }
    for v in data:
        ret["currency"].append(v["currency"])
        if v["party"]:
            if v["party_type"] == "Supplier":
                ret["supplier"].append(v["party"])
            elif v["party_type"] == "Customer":
                ret["customer"].append(v["party"])
                
    return ret


# [Internal]
def clean_bank_transactions(accounts):
    dt = "Bank Transaction"
    clean_entries(dt, [
        [dt, "bank_account", "in", accounts],
        [dt, "from_gocardless", "=", 1]
    ])


# [Internal]
def clean_bank_accounts(names, bank, company):
    dt = "Bank Account"
    filters = [
        [dt, "name", "in", names],
        [dt, "company", "=", company],
        [dt, "from_gocardless", "=", 1]
    ]
    if bank:
        filters.append([dt, "bank", "=", bank])
    clean_entries(dt, filters)


# [Internal]
def clean_bank(name):
    dt = "Bank"
    clean_entries(dt, [
        [dt, "name", "=", name],
        [dt, "from_gocardless", "=", 1]
    ])


# [Internal]
def clean_currency(names):
    dt = "Currency"
    clean_entries(dt, [
        [dt, "name", "in", names],
        [dt, "from_gocardless", "=", 1]
    ])


# [Internal]
def clean_supplier(names):
    dt = "Supplier"
    clean_entries(dt, [
        [dt, "name", "in", names],
        [dt, "from_gocardless", "=", 1]
    ])


# [Internal]
def clean_customer(names):
    dt = "Customer"
    clean_entries(dt, [
        [dt, "name", "in", names],
        [dt, "from_gocardless", "=", 1]
    ])


# [Internal]
def clean_sync_log(bank):
    from .sync_log import _LOG_DT_
    
    clean_entries(_LOG_DT_, [
        [_LOG_DT_, "bank", "=", bank]
    ])


# [Internal]
def clean_entries(dt, filters):
    names = frappe.get_all(
        dt,
        fields=["name"],
        filters=filters,
        pluck="name",
        ignore_permissions=True,
        strict=False
    )
    if not names or not isinstance(names, list):
        return 0
    
    for name in names:
        try:
            frappe.delete_doc(
                dt, name,
                ignore_permissions=True,
                ignore_missing=True,
                delete_permanently=True
            )
        except Exception:
            pass