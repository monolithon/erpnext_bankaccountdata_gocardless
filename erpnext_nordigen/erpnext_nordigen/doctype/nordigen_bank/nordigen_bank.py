# ERPNext Nordigen © 2023
# Author:  Ameen Ahmed
# Company: Level Up Marketing & Software Development Services
# Licence: Please refer to LICENSE file


import frappe
from frappe import _, throw
from frappe.model.document import Document
from frappe.utils import cint

from erpnext_nordigen.libs.nordigen import (
    get_doc,
    clear_doc_cache,
    enqueue_save_bank,
    enqueue_update_bank,
    add_bank_account,
    update_bank_account,
    send_bank_error
)


class NordigenBank(Document):
    def autoname(self):
        self.name = self.title
    
    def validate(self):
        if self.is_new():
            if frappe.db.exists(self.doctype, self.name):
                throw(_(self.doctype + " {0} already exist.").format(self.name))
            if not self.company:
                throw(_("Please select a company to create bank accounts under."))
            if not self.bank:
                throw(_("Please select a bank to link with Nordigen."))
            if not self.bank_id or not self.transaction_days:
                throw(_("The bank data is invalid."))
        else:
            is_valid = True
            try:
                old = self.get_doc_before_save()
                if (
                    old.company != self.company or
                    old.bank != self.bank or
                    old.bank_id != self.bank_id or
                    old.transaction_days != self.transaction_days
                ):
                    is_valid = False
            except Exception:
                pass
            
            if not is_valid:
                throw(_("You are not allowed to update the data."))
    
    
    def before_save(self):
        clear_doc_cache(self.doctype, self.name)
    
    
    def on_trash(self):
        settings = get_doc()
        
        if cint(settings.remove_actual_bank_transactions):
            try:
                accounts = [v.account for v in self.bank_accounts]
                frappe.db.delete("Bank Transaction", {
                    "bank_account": ["in", accounts],
                })
            except Exception:
                pass
        
        if cint(settings.remove_actual_bank_accounts):
            try:
                accounts = [v.account for v in self.bank_accounts]
                frappe.db.delete("Bank Account", {
                    "name": ["in", accounts],
                    "bank": self.bank,
                    "company": self.company
                })
            except Exception:
                pass
        
        if cint(settings.remove_actual_bank):
            try:
                frappe.db.delete("Bank", self.bank)
            except Exception:
                pass
        
        try:
            frappe.db.delete("Nordigen Sync Log", {"bank": self.name})
        except Exception:
            pass
    
    
    @frappe.whitelist(methods=["POST"])
    def save_link(self, auth_id, auth_expiry):
        if (
            not auth_id or not isinstance(auth_id, str) or
            not auth_expiry or not isinstance(auth_expiry, str)
        ):
            send_bank_error(
                {
                    "bank": self.bank,
                    "error": _(
                        "The Nordigen link data for \"{0}\" is invalid."
                    ).format(self.bank),
                }
            )
            return 0
        
        is_new = 1 if not self.auth_id or not self.bank_accounts else 0
        
        self.auth_id = auth_id
        self.auth_expiry = auth_expiry
        self.auth_status = "Linked"
        self.save()
        
        if is_new:
            enqueue_save_bank(self.name, self.bank, self.auth_id)
        else:
            enqueue_update_bank(self.name, self.bank, self.auth_id)
        return 1
    
    
    @frappe.whitelist(methods=["POST"])
    def store_bank_account(self, account):
        if not account or not isinstance(account, str):
            send_bank_error(
                {
                    "bank": self.bank,
                    "error": _(
                        "The Nordigen bank account data for \"{0}\" is invalid."
                    ).format(self.bank),
                }
            )
            return 0
        
        account_data = None
        for v in self.bank_accounts:
            if v.account == account and not getattr(v, "bank_account", ""):
                account_data = {
                    "account": v.account,
                    "account_id": v.account_id,
                    "account_type": v.account_type,
                    "account_no": v.account_no,
                    "iban": v.iban,
                    "is_default": 0
                }
                break
        
        if not account_data:
            send_bank_error(
                {
                    "bank": self.bank,
                    "error": _(
                        "The Nordigen bank account \"{0}\" is not part of {1}."
                    ).format(account, self.bank),
                }
            )
            return 0
        
        if not frappe.db.exists("Bank Account", {
            "bank": self.bank,
            "company": self.company,
            "is_default": 1
        }):
            account_data["is_default"] = 1
        
        return add_bank_account(self.name, self.company, self.bank, account_data)
    
    
    @frappe.whitelist(methods=["POST"])
    def update_bank_account(self, account, bank_account):
        if (
            not account or not isinstance(account, str) or
            not bank_account or not isinstance(bank_account, str)
        ):
            return 0
        
        account_data = None
        for v in self.bank_accounts:
            if v.account == account and not getattr(v, "bank_account", ""):
                account_data = v.account
                break
        
        if not account_data:
            send_bank_error(
                {
                    "bank": self.bank,
                    "error": _(
                        "The Nordigen bank account \"{0}\" is not part of {1}."
                    ).format(account, self.bank),
                }
            )
            return 0
        
        return update_bank_account(self.name, bank_account, account_data)