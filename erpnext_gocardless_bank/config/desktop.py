# ERPNext Gocardless Bank © 2023
# Author:  Ameen Ahmed
# Company: Level Up Marketing & Software Development Services
# Licence: Please refer to LICENSE file


from frappe import _


def get_data():
    return [
        {
            "module_name": "ERPNext Gocardless Bank",
            "color": "blue",
            "icon": "octicon octicon-plug",
            "type": "module",
            "label": _("ERPNext Gocardless Bank")
        }
    ]