# Expenses © 2024
# Author:  Ameen Ahmed
# Company: Level Up Marketing & Software Development Services
# Licence: Please refer to LICENSE file


import frappe


# [G Bank]
def enqueue_bank_trash(name, company, bank_ref, accounts_ref, account_types_ref):
    from .background import is_job_running
    
    job_id = f"gocardless-bank-trash-{name}"
    if not is_job_running(job_id):
        from .background import enqueue_job
        
        enqueue_job(
            "erpnext_gocardless_bank.libs.clean.clean_trash",
            job_id,
            queue="long",
            timeout=300000,
            name=name,
            bank=bank_ref,
            company=company,
            accounts=accounts_ref,
            account_types=account_types_ref
        )


# [Internal]
def clean_trash(name, bank, company, accounts, account_types):
    from .system import settings
    
    doc = settings()
    data = None
    if accounts and doc._clean_bank_transaction:
        if (
            doc._clean_currency or
            doc._clean_supplier or
            doc._clean_customer
        ):
            data = get_transactions_data(accounts)
        
        clean_bank_transactions(accounts)
    
    if accounts and doc._clean_bank_account:
        clean_bank_accounts(accounts, bank, company)
    
    if account_types and doc._clean_bank_account_type:
        clean_bank_account_types(account_types)
    
    if bank and doc._clean_bank:
        clean_bank(bank)
    
    if data:
        if doc._clean_currency and data["currency"]:
            clean_currency(data["currency"])
        
        if doc._clean_supplier and data["supplier"]:
            clean_supplier(data["supplier"])
        
        if doc._clean_customer and data["customer"]:
            clean_customer(data["customer"])
    
    clean_sync_log(name)


# [Internal]
def get_transactions_data(accounts):
    doc = frappe.qb.DocType("Bank Transaction")
    data = (
        frappe.qb.from_(doc)
        .select(
            doc.currency,
            doc.party_type,
            doc.party
        )
        .where(doc.bank_account.isin(accounts))
        .where(doc.from_gocardless == 1)
    ).run(as_dict=True)
    if not data or not isinstance(data, list):
        return None
    
    ret = {
        "currency": [],
        "supplier": [],
        "customer": [],
    }
    for i in range(len(data)):
        v = data.pop(0)
        if v["currency"] not in ret["currency"]:
            ret["currency"].append(v["currency"])
        if v["party"]:
            if v["party_type"] == "Supplier" and v["party"] not in ret["supplier"]:
                ret["supplier"].append(v["party"])
            elif v["party_type"] == "Customer" and v["party"] not in ret["customer"]:
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
    clean_entries(dt, [
        [dt, "name", "in", names],
        [dt, "bank", "=", bank],
        [dt, "company", "=", company],
        [dt, "from_gocardless", "=", 1]
    ])


# [Internal]
def clean_bank_account_types(names):
    dt = "Bank Account Type"
    clean_entries(dt, [
        [dt, "name", "in", names],
        [dt, "from_gocardless", "=", 1]
    ])


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
    names = get_entry_names(dt, filters)
    if not names:
        return 0
    
    links = get_links(dt)
    if links:
        update = []
        for p in list(links.keys()):
            fields = links.pop(p)
            data = get_linked_data(p, fields, names)
            if not data:
                continue
            
            gc = str(p).startswith("Gocardless")
            for i in range(len(data)):
                v = data.pop(0)
                for f in fields:
                    if not v.get(f, ""):
                        continue
                    
                    if not gc and v.get(f) not in update:
                        update.append(v.get(f))
                    elif gc and v.get(f) in update:
                        update.remove(v.get(f))
                    if v.get(f) in names:
                        names.remove(v.get(f))
        
        if update:
            for i in range(len(update)):
                frappe.db.set_value(
                    dt, update.pop(0), {"from_gocardless": 0},
                    update_modified=False
                )
    
    if not names:
        return 0
    
    frappe.flags.from_gocardless_trash = 1
    for i in range(len(names)):
        try:
            frappe.delete_doc(
                dt, names.pop(0),
                ignore_permissions=True,
                ignore_missing=True,
                delete_permanently=True
            )
        except Exception:
            pass
    
    frappe.flags.pop("from_gocardless_trash", 0)


# [Internal]
def get_entry_names(dt, filters):
    data = frappe.get_all(
        dt,
        fields=["name"],
        filters=filters,
        pluck="name",
        ignore_permissions=True,
        strict=False
    )
    if not data or not isinstance(data, list):
        data = None
    
    return data


# [Internal]
def get_links(dt):
    linked = {}
    doc = frappe.qb.DocType("DocField")
    data = (
        frappe.qb.from_(doc)
        .select(
            doc.parent,
            doc.fieldname
        )
        .where(doc.parenttype == "DocType")
        .where(doc.parentfield == "fields")
        .where(doc.fieldtype == "Link")
        .where(doc.options == dt)
    ).run(as_dict=True)
    if data and isinstance(data, list):
        for v in data:
            if v["parent"] not in linked:
                linked[v["parent"]] = []
            linked[v["parent"]].append(str(v["fieldname"]).strip())
    
    doc = frappe.qb.DocType("Custom Field")
    data = (
        frappe.qb.from_(doc)
        .select(
            doc.dt,
            doc.fieldname
        )
        .where(doc.fieldtype == "Link")
        .where(doc.options == dt)
    ).run(as_dict=True)
    if data and isinstance(data, list):
        for v in data:
            if v["dt"] not in linked:
                linked[v["dt"]] = []
            linked[v["dt"]].append(str(v["fieldname"]).strip())
    
    return linked


# [Internal]
def get_linked_data(dt, fields, data):
    doc = frappe.qb.DocType(dt)
    qry = frappe.qb.from_(doc)
    filters = []
    for f in fields:
        f = doc.field(f)
        qry = qry.select(f)
        filters.append(f.isin(data))
    
    if len(filters) > 1:
        from pypika.terms import Criterion
        
        qry = qry.where(Criterion.any(filters))
    else:
        qry = qry.where(filters.pop(0))
    
    data = qry.run(as_dict=True)
    if not data or not isinstance(data, list):
        data = None
    
    return data