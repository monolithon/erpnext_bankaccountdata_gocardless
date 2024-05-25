# ERPNext Gocardless Bank © 2024
# Author:  Ameen Ahmed
# Company: Level Up Marketing & Software Development Services
# Licence: Please refer to LICENSE file


# [System]
def update_access(row, client):
    from .datetime import now_utc
        
    now = now_utc()
    if not row.access_token:
        return access_connect(row, client, now)
    
    from .datetime import to_datetime_obj
    
    if to_datetime_obj(row.access_expiry) > now:
        return 0
    
    if to_datetime_obj(row.refresh_expiry) > now:
        return access_refresh(row, client, now)
    
    return access_connect(row, client, now)


# [Internal]
def access_connect(row, client, now):
    client.connect(row.secret_id, row.secret_key)
    return update_access_data(row, client, now, True)


# [Internal]
def access_refresh(row, client, now):
    client.refresh(row.refresh_token)
    return update_access_data(row, client, now)


# [Internal]
def update_access_data(row, client, now, _all=False):
    data = client.get_token()
    if not data or not isinstance(data, dict):
        return -1
    
    if _all and "refresh" not in data:
        return -1
    
    from frappe.utils import cint
    
    from .datetime import add_datetime
    
    if "refresh" in data:
        row.refresh_token = data["refresh"]
        row.refresh_expiry = add_datetime(
            now,
            seconds=cint(data["refresh_expires"]),
            as_string=True
        )
    
    row.access_token = data["access"]
    row.access_expiry = add_datetime(
        now,
        seconds=cint(data["access_expires"]),
        as_string=True
    )