# ERPNext Nordigen © 2023
# Author:  Ameen Ahmed
# Company: Level Up Marketing & Software Development Services
# Licence: Please refer to LICENSE file


from frappe import __version__ as frappe_version


app_name = "erpnext_nordigen"
app_title = "ERPNext Nordigen"
app_publisher = "Ameen Ahmed (Level Up)"
app_description = "Nordigen integration for ERPNext."
app_icon = "octicon octicon-plug"
app_color = "blue"
app_email = "kid1194@gmail.com"
app_license = "MIT"


is_frappe_above_v13 = int(frappe_version.split('.')[0]) > 13


app_include_js = [
    "nordigen.bundle.js"
] if is_frappe_above_v13 else [
    "/assets/erpnext_nordigen/js/nordigen.bundle.js"
]

doctype_js = {
    "Bank Account" : "public/js/bank_account.bundle.js",
    "Bank Transaction" : "public/js/bank_transaction.bundle.js"
}


after_install = "erpnext_nordigen.setup.install.after_install"
before_uninstall = "erpnext_nordigen.setup.uninstall.before_uninstall"


scheduler_events = {
    "daily": [
        "erpnext_nordigen.libs.nordigen.update_banks_status"
    ],
    "cron": {
        "0 */6 * * *": [
            "erpnext_nordigen.libs.nordigen.auto_sync"
        ],
    }
}