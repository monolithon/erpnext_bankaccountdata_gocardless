# ERPNext Gocardless Bank © 2024
# Author:  Ameen Ahmed
# Company: Level Up Marketing & Software Development Services
# Licence: Please refer to LICENSE file


import frappe


# [G Bank, G Bank Form, Bank]
@frappe.whitelist(methods=["POST"])
def get_company_country(company):
    if not company or not isinstance(company, str):
        return 0
    
    from .cache import get_cached_value
    
    data = get_cached_value("Company", company, "country")
    if not data or not isinstance(data, str):
        return 0
    
    return data


# [Bank Account]
def get_company_currency(name):
    from .cache import get_cached_value
    
    data = get_cached_value("Company", name, "default_currency")
    if not data or not isinstance(data, str):
        data = None
    
    return data


# [G Bank Form]
@frappe.whitelist()
def search_companies(doctype, txt, searchfield, start, page_len, filters, as_dict=False):
    from .search import (
        filter_search,
        prepare_data
    )
    from .system import settings
    
    doc = settings()
    companies = [v.company for v in doc.access]
    
    dt = "Company"
    doc = frappe.qb.DocType(dt)
    qry = (
        frappe.qb.from_(doc)
        .select(
            doc.name.as_("label"),
            doc.name.as_("value")
        )
        .where(doc.name.isin(companies))
        .where(doc.is_group == 0)
    )
    qry = filter_search(doc, qry, dt, txt, doc.name, "name")
    data = qry.run(as_dict=as_dict)
    data = prepare_data(data, dt, "name", txt, as_dict)
    return data