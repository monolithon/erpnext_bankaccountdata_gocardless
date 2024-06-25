# ERPNext Gocardless Bank © 2024
# Author:  Ameen Ahmed
# Company: Level Up Marketing & Software Development Services
# Licence: Please refer to LICENSE file


import frappe


# [G Bank Form]
@frappe.whitelist(methods=["POST"])
def get_company_country(company):
    if not company or not isinstance(company, str):
        return 0
    
    data = get_company_country_name(company)
    return data if data else 0


# [G Bank, Bank]
def get_company_country_name(company: str):
    from .cache import get_cached_value
    
    data = get_cached_value("Company", company, "country")
    if not data or not isinstance(data, str):
        return None
    
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
    from .system import get_access_companies
    
    companies = get_access_companies()
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