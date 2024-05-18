# ERPNext Gocardless Bank © 2024
# Author:  Ameen Ahmed
# Company: Level Up Marketing & Software Development Services
# Licence: Please refer to LICENSE file


app_name = "erpnext_gocardless_bank"
app_title = "ERPNext Gocardless Bank"
app_publisher = "Ameen Ahmed (Level Up)"
app_description = "Gocardless bank services integration for ERPNext."
app_icon = "octicon octicon-plug"
app_color = "blue"
app_email = "kid1194@gmail.com"
app_license = "MIT"


before_install = "erpnext_gocardless_bank.setup.install.before_install"
after_sync = "erpnext_gocardless_bank.setup.install.after_sync"
after_uninstall = "erpnext_gocardless_bank.setup.uninstall.after_uninstall"


doctype_js = {
    "Gocardless Bank" : "public/js/gocardless.bundle.js",
    "Gocardless Sync Log" : "public/js/gocardless.bundle.js",
    "Gocardless Settings" : "public/js/gocardless.bundle.js",
    
    "Bank Account" : "public/js/bank_account.bundle.js",
    "Bank Transaction" : "public/js/bank_transaction.bundle.js"
}


doctype_list_js = {
    "Gocardless Bank" : "public/js/gocardless.bundle.js",
    "Gocardless Sync Log" : "public/js/gocardless.bundle.js"
}


scheduler_events = {
    "daily": [
        "erpnext_gocardless_bank.libs.schedule.update_banks_status"
    ],
    "cron": {
        "0 */6 * * *": [
            "erpnext_gocardless_bank.libs.schedule.auto_sync"
        ],
    }
}


required_apps = ["erpnext"]