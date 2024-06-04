# Expenses © 2024
# Author:  Ameen Ahmed
# Company: Level Up Marketing & Software Development Services
# Licence: Please refer to LICENSE file


from datetime import datetime


# [Access, Internal]
def now_utc():
    return datetime.utcnow()


# [Bank Transaction, Schedule]
def today_utc_date(dt=None):
    if not dt:
        dt = now_utc()
    
    return to_date(dt)


# [Bank Transaction]
def today_utc_datetime(dt=None):
    if not dt:
        dt = now_utc()
    
    return to_datetime(dt)


# [Bank Transaction, Schedule, Internal]
def to_date(dt):
    from frappe.utils import DATE_FORMAT
    
    return dt.strftime(DATE_FORMAT)


# [Bank Transaction, Schedule, Internal]
def to_date_obj(dt: str):
    from frappe.utils import getdate
    
    return getdate(dt)


# [Internal]
def to_datetime(dt):
    from frappe.utils import DATETIME_FORMAT
    
    return dt.strftime(DATETIME_FORMAT)


# [Access]
def to_datetime_obj(dt: str):
    from frappe.utils import get_datetime
    
    return get_datetime(dt)


# [Access, System]
def add_datetime(dt: str, **kwargs):
    from frappe.utils import add_to_date
    
    return add_to_date(dt, as_datetime=True, **kwargs)


# [Bank Transaction, Schedule]
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


# [Bank Transaction, Schedule]
def add_date(dt: str, **kwargs):
    from frappe.utils import add_to_date
    
    return add_to_date(dt, as_datetime=False, **kwargs)


# [Bank Transaction]
def date_to_datetime(dt: str, start=False):
    if start:
        dt = dt.split(" ")[0]
        return f"{dt} 00:00:00.000"
    
    dt = to_date_obj(dt)
    dt = datetime.combine(dt, datetime.utcnow().time())
    return to_datetime(dt)