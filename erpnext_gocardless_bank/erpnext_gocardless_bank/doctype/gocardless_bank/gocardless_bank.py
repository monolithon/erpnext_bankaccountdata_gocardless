# ERPNext Gocardless Bank © 2023
# Author:  Ameen Ahmed
# Company: Level Up Marketing & Software Development Services
# Licence: Please refer to LICENSE file


from frappe import _
from frappe.model.document import Document
from frappe.utils import cint

from erpnext_gocardless_bank.libs import clear_doc_cache


class GocardlessBank(Document):
    def before_insert(self):
        self._check_app_status()
        self._set_defaults()
    
    
    def before_validate(self):
        self._check_app_status()
        if self.is_new() or self._is_draft:
            self._set_defaults()
    
    
    def validate(self):
        self._check_app_status()
        if self.is_new() or self._is_draft:
            if not self.company:
                self._error(_("A valid company is required."))
            if not self.country:
                self._error(_("Company \"{0}\" doesn't have a valid country.").format(self.company))
            if not self.bank:
                self._error(_("A valid bank is required."))
            if not self.bank_id:
                self._error(_("Bank id for selected bank isn't found."))
            if (
                not self.is_new() and
                self.has_value_changed("bank") and
                self.auth_id and
                (
                    not self.has_value_changed("auth_id") or
                    not self.has_value_changed("auth_expiry")
                )
            ):
                self.auth_id = None
                self.auth_expiry = None
    
    
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
        if not self.auth_id or not self.auth_expiry:
            self._error(_("Bank must be authorized before being submitted."))
        
        clear_doc_cache(self.doctype, self.name)
        if self.auth_status != "Linked":
            self.auth_status = "Linked"
        if not self.bank_ref:
            from erpnext_gocardless_bank.libs import add_bank
            
            ref = add_bank(self.bank)
            if ref:
                from erpnext_gocardless_bank.libs import enqueue_save_bank
                
                self.bank_ref = ref
                enqueue_save_bank(self.name, self.bank, self.company, self.auth_id, self.bank_ref)
            else:
                self._error(_("ERPNext: Unable to create bank \"{0}\".").format(self.bank))
    
    
    def on_update(self):
        self._clean_flags()
    
    
    def before_update_after_submit(self):
        self._check_app_status()
        clear_doc_cache(self.doctype, self.name)
    
    
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
        
        from erpnext_gocardless_bank.libs import enqueue_bank_trash
        
        enqueue_bank_trash(self)
    
    
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
    
    
    def _set_defaults(self):
        if self.company:
            if self.is_new() or self.has_value_changed("company"):
                from erpnext_gocardless_bank.libs import get_company_country
                
                country = get_company_country(self.company)
                if not country and self.country:
                    self.country = None
                elif country and (not self.country or self.country != country):
                    self.country = country
            
            if (
                self.bank and self.country and
                (not self.bank_id or self.has_value_changed("bank"))
            ):
                from erpnext_gocardless_bank.libs import get_banks
                
                self.bank_id = None
                banks = get_banks(self.company, self.country)
                if banks and isinstance(banks, list):
                    for v in banks:
                        if v and isinstance(v, dict) and v.get("name", "") == self.bank:
                            self.bank_id = v.get("id", "")
                            break
                    
                    banks.clear()
        
        if cint(self.transaction_days) < 1:
            self.transaction_days = 180
    
    
    def _check_app_status(self):
        if not self.flags.get("status_checked", 0):
            from erpnext_gocardless_bank.libs import check_app_status
            
            check_app_status()
            self.flags.status_checked = 1
    
    
    def _clean_flags(self):
        keys = [
            "status_checked"
        ]
        for i in range(len(keys)):
            self.flags.pop(keys.pop(0), None)
    
    
    def _error(self, msg):
        from erpnext_gocardless_bank.libs import error
        
        self._clean_flags()
        error(msg, _(self.doctype))