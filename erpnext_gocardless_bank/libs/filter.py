# ERPNext Gocardless Bank © 2024
# Author:  Ameen Ahmed
# Company: Level Up Marketing & Software Development Services
# Licence: Please refer to LICENSE file


import frappe


# [G Settings]
def companies_filter(names: list, attrs: dict|None=None):
    return all_filter("Company", "name", names, attrs)


# [Internal]
def all_filter(
    dt: str, field: str|list, names: list, attrs: dict|None=None,
    enabled: bool|None=None, status_col: str="disabled", status_val: int=0
):
    if isinstance(field, str):
        field = [field]
    
    flen = len(field)
    if flen > 2:
        field = field[:2]
        flen = 2
    
    filters = [[dt, field[0], "in", list(set(names))]]
    if attrs:
        for k in attrs:
            if isinstance(attrs[k], list):
                if len(attrs[k]) > 1 and isinstance(attrs[k][1], list):
                    filters.append([dt, k, attrs[k][0], attrs[k][1]])
                else:
                    filters.append([dt, k, "in", attrs[k]])
            else:
                filters.append([dt, k, "=", attrs[k]])
    
    if enabled == True:
        filters.append([dt, status_col, "=", status_val])
    elif enabled == False:
        filters.append([dt, status_col, "!=", status_val])
    
    data = frappe.get_all(
        dt,
        fields=field,
        filters=filters,
        pluck=field[0] if flen == 1 else None,
        ignore_permissions=True,
        strict=False
    )
    if not data or not isinstance(data, list):
        return None
    
    if flen == 1:
        return [v for v in data if v in names]
    
    return {v[field[0]]:v[field[1]] for v in data if v[field[0]] in names}