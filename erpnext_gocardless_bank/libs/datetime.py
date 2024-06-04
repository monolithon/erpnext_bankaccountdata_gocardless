# Expenses © 2024
# Author:  Ameen Ahmed
# Company: Level Up Marketing & Software Development Services
# Licence: Please refer to LICENSE file


# [Access, Internal]
def now_obj():
    from datetime import datetime
    
    return datetime.utcnow()


# [Bank Transaction, Schedule]
def today_date(dt=None):
    return to_date(dt or now_obj())


# [Bank Transaction]
def today_datetime(dt=None):
    return to_datetime(dt or now_obj())


# [Bank Transaction, Internal]
def to_date(dt):
    from frappe.utils import DATE_FORMAT
    
    return dt.strftime(DATE_FORMAT)


# [Internal]
def to_date_obj(dt):
    if not isinstance(dt, str):
        return dt
    if dt == "now":
        return now_obj()
    
    from frappe.utils import getdate
    
    return getdate(dt)


# [Internal]
def to_datetime(dt):
    from frappe.utils import DATETIME_FORMAT
    
    return dt.strftime(DATETIME_FORMAT)


# [Internal]
def to_datetime_obj(dt):
    if not isinstance(dt, str):
        return dt
    if dt == "now":
        return now_obj()
    
    from frappe.utils import get_datetime
    
    return get_datetime(dt)


# [Access, System]
def add_datetime(dt: str, **kwargs):
    from frappe.utils import add_to_date
    
    return add_to_date(dt, as_datetime=True, **kwargs)


# [Bank Transaction]
def reformat_date(dt: str, df=None):
    from frappe.utils import formatdate, DATE_FORMAT
    
    try:
        return formatdate(dt, DATE_FORMAT)
    except Exception:
        try:
            ret = to_date_obj(dt)
            if ret:
                return ret.strftime(DATE_FORMAT)
        except Exception:
            pass
    
    return df


# [Schedule]
def reformat_datetime(dt: str, df=None):
    from frappe.utils import format_datetime, DATETIME_FORMAT
    
    try:
        return format_datetime(dt, DATETIME_FORMAT)
    except Exception:
        try:
            ret = to_datetime_obj(dt)
            if ret:
                return ret.strftime(DATETIME_FORMAT)
        except Exception:
            pass
    
    return df


# [Bank Transaction, Schedule]
def add_date(dt: str, **kwargs):
    from frappe.utils import add_to_date
    
    return add_to_date(dt, as_datetime=False, **kwargs)


# [Bank Transaction]
def date_to_datetime(dt: str, start=False):
    if start:
        dt = dt.split(" ")[0]
        return f"{dt} 00:00:00.000"
    
    from datetime import datetime
    
    dt = to_date_obj(dt)
    dt = datetime.combine(dt, datetime.utcnow().time())
    return to_datetime(dt)


# [Bank Transaction, Schedule, Internal]
def dates_diff_days(sdt, edt):
    from frappe.utils import cint
    
    sdt = to_date_obj(sdt)
    edt = to_date_obj(edt)
    return cint((edt - sdt).days)


# [Internal]
def dates_diff_seconds(sdt, edt):
    from frappe.utils import cint
    
    sdt = to_datetime_obj(sdt)
    edt = to_datetime_obj(edt)
    return cint((edt - sdt).total_seconds())


# [Bank Transaction]
def get_date_obj_range(fdt, tdt):
    fdt = to_date_obj(fdt)
    days = dates_diff_days(fdt, tdt)
    if days <= 0:
        return [fdt]
    
    from datetime import datetime
    
    return [fdt + datetime.timedelta(days=x) for x in range(days + 1)]


# [Bank Transaction, Schedule]
def is_date_gt(fdt, sdt):
    return dates_diff_days(sdt, fdt) > 0


# [Internal]
def is_datetime_gt(fdt, sdt):
    return dates_diff_seconds(sdt, fdt) > 0


# [Access]
def is_now_datetime_gt(dt):
    return is_datetime_gt(now_obj(), dt)