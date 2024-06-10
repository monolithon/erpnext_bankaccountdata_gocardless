# ERPNext Gocardless Bank © 2023
# Author:  Ameen Ahmed
# Company: Level Up Marketing & Software Development Services
# Licence: Please refer to LICENSE file


from frappe import _
from frappe.model.document import Document
from frappe.utils import cint

from erpnext_gocardless_bank.libs import clear_doc_cache


class GocardlessBank(Document):
    _def_transaction_days = 90
    
    
    def before_insert(self):
        self._check_app_status()
        self._set_defaults()
    
    
    def before_validate(self):
        self._check_app_status()
        if self._is_draft:
            self._set_defaults()
    
    
    def validate(self):
        self._check_app_status()
        if self._is_draft:
            self._set_defaults()
            if not self.company:
                self._add_error(_("A valid company is required."))
            elif not self.country:
                self._add_error(_("Company \"{0}\" doesn't have a valid country.").format(self.company))
            if not self.bank:
                self._add_error(_("A valid bank is required."))
            elif self.flags.get("bank_validate_error", 0):
                self._add_error(_("Unable to validate support for \"{0}\" with Gocardless.").format(self.bank))
            elif self.flags.get("bank_support_error", 0):
                self._add_error(_("\"{0}\" isn't supported by Gocardless.").format(self.bank))
            elif self.company and self.country and not self.bank_id:
                self._add_error(_("Unable to get Gocardless Bank ID for \"{0}\".").format(self.bank))
            
            self._throw_errors()
    
    
    def before_rename(self, olddn, newdn, merge=False):
        self._check_app_status()
        
        super(GocardlessBank, self).before_rename(olddn, newdn, merge)
        
        clear_doc_cache(self.doctype, olddn)
        self._clean_flags()
    
    
    def before_save(self):
        self._check_app_status()
        clear_doc_cache(self.doctype, self.name)
    
    
    def before_submit(self):
        self._check_app_status()
        clear_doc_cache(self.doctype, self.name)
    
    
    def on_update(self):
        self._clean_flags()
    
    
    def before_update_after_submit(self):
        self._check_app_status()
        clear_doc_cache(self.doctype, self.name)
        if self._is_auth and not self.bank_ref:
            from erpnext_gocardless_bank.libs import add_bank
            
            ref = add_bank(self.bank)
            if ref:
                from erpnext_gocardless_bank.libs import enqueue_sync_bank
                
                self.bank_ref = ref
                self.save(ignore_permissions=True)
                enqueue_sync_bank(self.name, self.bank, self.company, self.auth_id)
            else:
                self._error(_("Unable to add \"{0}\" to ERPNext.").format(self.bank))
    
    
    def on_update_after_submit(self):
        self._clean_flags()
    
    
    def before_cancel(self):
        self._check_app_status()
        clear_doc_cache(self.doctype, self.name)
    
    
    def on_cancel(self):
        self._clean_flags()
    
    
    def on_trash(self):
        self._check_app_status()
        if self._is_submitted:
            self._error(_("Submitted bank can't be removed."))
        
        clear_doc_cache(self.doctype, self.name)
        if self.bank_ref:
            from erpnext_gocardless_bank.libs import enqueue_bank_trash
            
            enqueue_bank_trash(
                self.name,
                self.company,
                self.bank_ref,
                [v.bank_account_ref for v in self.bank_accounts if v.bank_account_ref]
            )
    
    
    def after_delete(self):
        self._clean_flags()
    
    
    @property
    def _is_draft(self):
        return cint(self.docstatus) == 0
    
    
    @property
    def _is_submitted(self):
        return cint(self.docstatus) == 1
    
    
    @property
    def _is_cancelled(self):
        return cint(self.docstatus) == 2
    
    
    @property
    def _is_auth(self):
        return self.auth_id and self.auth_expiry and self.auth_status == "Linked"
    
    
    def _set_defaults(self):
        if self.flags.get("defaults_set", 0):
            return 0
        
        self.flags.defaults_set = 1
        if not self.company:
            return self._reset_bank()
        
        if self.is_new() or self.has_value_changed("company"):
            from erpnext_gocardless_bank.libs import get_company_country
            
            country = get_company_country(self.company)
            if not country and self.country:
                self.country = None
            elif country and self.country != country:
                self.country = country
        
        if not self.country or not self.bank:
            return self._reset_bank()
        
        if self.is_new() or self.has_value_changed("bank"):
            from erpnext_gocardless_bank.libs import get_banks
            
            banks = get_banks(self.company, self.country)
            if not banks:
                self.flags.bank_validate_error = 1
                return self._reset_bank()
            
            if not isinstance(banks, list):
                from erpnext_gocardless_bank.libs import (
                    store_error,
                    log_error
                )
                
                err = None
                if isinstance(banks, dict) and banks.get("error", ""):
                    err = banks["error"]
                
                if not err:
                    from erpnext_gocardless_bank.libs import store_error
                    
                    store_error({
                        "error": "Gocardless banks list received is invalid.",
                        "data": banks
                    })
                    err = _("Gocardless banks list received is invalid.")
                
                self.flags.bank_validate_error = 1
                log_error(err)
                return self._reset_bank()
            
            for i in range(len(banks)):
                v = banks.pop(0)
                if v["name"] == self.bank:
                    return self._reset_bank(v)
            
            self.flags.bank_support_error = 1
            self._reset_bank()
    
    
    def _reset_bank(self, val=None):
        if not val:
            val = {"id": None, "transaction_total_days": 0}
        
        if self.bank_id != val["id"]:
            self.bank_id = val["id"]
        tdays = cint(val["transaction_total_days"])
        if tdays < 1:
            tdays = self._def_transaction_days
        if cint(self.transaction_days) != tdays:
            self.transaction_days = tdays
    
    
    def _check_app_status(self):
        if not self.flags.get("status_checked", 0):
            from erpnext_gocardless_bank.libs import check_app_status
            
            check_app_status()
            self.flags.status_checked = 1
    
    
    def _clean_flags(self):
        keys = [
            "error_list",
            "defaults_set",
            "bank_validate_error",
            "bank_support_error",
            "status_checked"
        ]
        for i in range(len(keys)):
            self.flags.pop(keys.pop(0), None)
    
    
    def _add_error(self, msg):
        if not self.flags.get("error_list", 0):
            self.flags.error_list = []
        self.flags.error_list.append(msg)
    
    
    def _throw_errors(self):
        if self.flags.get("error_list", 0):
            msg = self.flags.error_list
            if len(msg) == 1:
                msg = msg.pop(0)
            else:
                msg = msg.copy()
            
            self._error(msg)
    
    
    def _error(self, msg):
        from erpnext_gocardless_bank.libs import error
        
        self._clean_flags()
        error(msg, _(self.doctype))