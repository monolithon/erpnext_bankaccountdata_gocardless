# ERPNext Gocardless Bank © 2024
# Author:  Ameen Ahmed
# Company: Level Up Marketing & Software Development Services
# Licence: Please refer to LICENSE file


# [System]
def update_access(row, client):
    if not row.access_token:
        return access_connect(row, client)
    
    from .datetime import is_now_datetime_gt
    
    if not is_now_datetime_gt(row.access_expiry):
        return 0
    
    if not is_now_datetime_gt(row.refresh_expiry):
        return access_refresh(row, client)
    
    return access_connect(row, client)


# [Internal]
def access_connect(row, client):
    client.connect(row.secret_id, row.secret_key)
    return update_access_data(row, client, True)


# [Internal]
def access_refresh(row, client):
    client.refresh(row.refresh_token)
    return update_access_data(row, client)


# [Internal]
def update_access_data(row, client, _all=False):
    data = client.get_token()
    if not data or not isinstance(data, dict):
        return -1
    
    if _all and "refresh" not in data:
        return -1
    
    from frappe.utils import cint
    
    from .datetime import now_obj, add_datetime
    
    now = now_obj()
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