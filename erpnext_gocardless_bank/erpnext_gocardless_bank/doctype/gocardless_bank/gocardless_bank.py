# ERPNext Gocardless Bank © 2023
# Author:  Ameen Ahmed
# Company: Level Up Marketing & Software Development Services
# Licence: Please refer to LICENSE file


import frappe
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
        self._set_defaults()
    
    
    def validate(self):
        self._check_app_status()
        if not self.name:
            self._error(_("A valid name is required."))
        if self.is_new():
            self._validate_new_data()
        else:
            self._validate_old_data()
    
    
    def before_rename(self, olddn, newdn, merge=False):
        self._check_app_status()
        
        super(GocardlessBank, self).before_rename(olddn, newdn, merge)
        
        clear_doc_cache(self.doctype, olddn)
        self._clean_app_status()
    
    
    def before_save(self):
        self._check_app_status()
        clear_doc_cache(self.doctype, self.name)
    
    
    def on_update(self):
        self._clean_app_status()
    
    
    def on_trash(self):
        self._check_app_status()
        
        from erpnext_gocardless_bank.libs import enqueue_bank_trash
        
        enqueue_bank_trash(self)
    
    
    def after_delete(self):
        clear_doc_cache(self.doctype, self.name)
        self._clean_app_status()
    
    
    def _set_defaults(self):
        if self.company:
            from erpnext_gocardless_bank import get_company_country
            
            country = get_company_country(self.company)
            if not country and self.country:
                self.country = None
            elif country and (not self.country or self.country != country):
                self.country = country
            
            if not self.bank_id and self.bank and self.country:
                from erpnext_gocardless_bank.libs import get_banks
                
                banks = get_banks(self.company, self.country)
                if banks and isinstance(banks, list):
                    for v in banks:
                        if v and isinstance(v, dict) and v.get("name", "") == self.bank:
                            self.bank_id = v.get("id", "")
                            break
                    
                    banks.clear()
        
        if cint(self.transaction_days) < 1:
            self.transaction_days = 180
    
    
    def _validate_new_data(self):
        if not self.company:
            self._error(_("A valid company is required."))
        if not self.country:
            self._error(_("Company \"{0}\" doesn't have a valid country.").format(self.company))
        if not self.bank:
            self._error(_("A valid bank is required."))
        if not self.bank_id:
            self._error(_("Bank id for selected bank isn't found."))
    
    
    def _validate_old_data(self):
        doc = self.get_doc_before_save()
        if not doc:
            self.load_doc_before_save()
            doc = self.get_doc_before_save()
            if not doc:
                self._error(_("Unable to load data before save."))
        
        keys = [
            "company",
            "country",
            "bank",
            "bank_id",
            "transaction_days"
        ]
        for i in range(len(keys)):
            k = keys.pop(0)
            if (
                (i < 4 and (doc.get(k, "") != self.get(k, "") or not self.get(k, ""))) or
                (i == 4 and (cint(doc.get(k, 0)) != cint(self.get(k, 0)) or cint(self.get(k, 0)) < 1))
            ):
                self._error(_("Set once data has been modified."))
    
    
    def _check_app_status(self):
        if not self.flags.get("status_checked", False):
            from erpnext_gocardless_bank.libs import check_app_status
            
            check_app_status()
            self.flags.status_checked = True
    
    
    def _clean_app_status(self):
        self.flags.pop("status_checked", False)
    
    
    def _error(self, msg):
        from erpnext_gocardless_bank.libs import error
        
        self._clean_app_status()
        error(msg, _(self.doctype))