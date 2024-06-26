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
    
    "Bank" : "public/js/doctype/bank.bundle.js",
    "Bank Account" : "public/js/doctype/bank_account.bundle.js",
    "Bank Account Type" : "public/js/doctype/bank_account_type.bundle.js",
    "Bank Transaction" : "public/js/doctype/bank_transaction.bundle.js",
    "Currency" : "public/js/doctype/currency.bundle.js",
    "Supplier" : "public/js/doctype/supplier.bundle.js",
    "Customer" : "public/js/doctype/customer.bundle.js",
}


doctype_list_js = {
    "Gocardless Bank" : "public/js/gocardless.bundle.js",
    "Gocardless Sync Log" : "public/js/gocardless.bundle.js"
}


doc_events = {
    "Bank": {
        "before_save": "erpnext_gocardless_bank.libs.crud.bank.before_save_event",
        "on_trash": "erpnext_gocardless_bank.libs.crud.bank.on_trash_event"
    },
    "Bank Account": {
        "before_save": "erpnext_gocardless_bank.libs.crud.bank_account.before_save_event",
        "on_trash": "erpnext_gocardless_bank.libs.crud.bank_account.on_trash_event"
    },
    "Bank Account Type": {
        "before_save": "erpnext_gocardless_bank.libs.crud.bank_account_type.before_save_event",
        "on_trash": "erpnext_gocardless_bank.libs.crud.bank_account_type.on_trash_event"
    },
    "Bank Transaction": {
        "before_update_after_submit": "erpnext_gocardless_bank.libs.crud.bank_transaction.before_update_after_submit_event",
        "before_cancel": "erpnext_gocardless_bank.libs.crud.bank_transaction.before_cancel_event",
        "on_trash": "erpnext_gocardless_bank.libs.crud.bank_transaction.on_trash_event"
    },
    "Currency": {
        "before_save": "erpnext_gocardless_bank.libs.crud.currency.before_save_event",
        "on_trash": "erpnext_gocardless_bank.libs.crud.currency.on_trash_event"
    },
    "Supplier": {
        "before_save": "erpnext_gocardless_bank.libs.crud.supplier.before_save_event",
        "on_trash": "erpnext_gocardless_bank.libs.crud.supplier.on_trash_event"
    },
    "Customer": {
        "before_save": "erpnext_gocardless_bank.libs.crud.customer.before_save_event",
        "on_trash": "erpnext_gocardless_bank.libs.crud.customer.on_trash_event"
    }
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