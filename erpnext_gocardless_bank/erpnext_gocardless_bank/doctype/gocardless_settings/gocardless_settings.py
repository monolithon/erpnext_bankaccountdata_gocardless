# ERPNext Gocardless Bank © 2024
# Author:  Ameen Ahmed
# Company: Level Up Marketing & Software Development Services
# Licence: Please refer to LICENSE file


from frappe import _
from frappe.utils import cint
from frappe.model.document import Document


class GocardlessSettings(Document):
    def before_validate(self):
        self._set_defaults()
    
    
    def validate(self):
        self._validate_access()
    
    
    def before_save(self):
        from erpnext_gocardless_bank.libs import clear_doc_cache
        
        clear_doc_cache(self.doctype)
        if self.has_value_changed("enabled"):
            self.flags.emit_change = True
    
    
    def on_update(self):
        if self.flags.pop("emit_change", False):
            from erpnext_gocardless_bank import __production__
            
            from erpnext_gocardless_bank.libs import emit_status_changed
        
            emit_status_changed({
                "is_enabled": 1 if self.is_enabled else 0,
                "is_debug": 0 if __production__ else 1
            })
    
    
    @property
    def is_enabled(self):
        return cint(self.enabled) > 0
    
    
    @property
    def clean_bank(self):
        return cint(self.clean_bank_dt) > 0
    
    
    @property
    def clean_bank_account(self):
        return cint(self.clean_bank_account_dt) > 0
    
    
    @property
    def clean_bank_transaction(self):
        return cint(self.clean_bank_transaction_dt) > 0
    
    
    @property
    def clean_currency(self):
        return cint(self.clean_currency_dt) > 0
    
    
    @property
    def clean_supplier(self):
        return cint(self.clean_supplier_dt) > 0
    
    
    @property
    def clean_customer(self):
        return cint(self.clean_customer_dt) > 0
    
    
    def _set_defaults(self):
        if self.clean_bank:
            if not self.clean_bank_account:
                self.clean_bank_account_dt = 1
            if not self.clean_bank_transaction:
                self.clean_bank_transaction_dt = 1
        
        ign = "Ignore"
        if (
            self.clean_currency and
            self.bank_account_currency_doesnt_exist === ign and
            self.bank_transaction_currency_doesnt_exist === ign
        ):
            self.clean_currency_dt = 0
        if (
            self.clean_supplier and (
                self.supplier_exist_in_transaction === ign or
                self.supplier_in_transaction_doesnt_exist === ign
            )
        ):
            self.clean_supplier_dt = 0
        if (
            self.clean_customer and (
                self.customer_exist_in_transaction === ign or
                self.customer_in_transaction_doesnt_exist === ign
            )
        ):
            self.clean_customer_dt = 0
    
    
    def _validate_access(self):
        if not self.access:
            self._error(_("At least one valid company access data is required."))
        
        if not self.has_value_changed("access"):
            return 0
        
        from erpnext_gocardless_bank.libs import (
            companies_filter,
            is_valid_secret_id,
            is_valid_secret_key
        )
        
        exist = companies_filter(
            [v.company for v in self.access if v.company],
            {is_group: 0}
        )
        for i, v in enumerate(self.access):
            if not v.company:
                self._error(_("A valid access company in row #{0} is required.").format(i))
            if v.company not in exist:
                self._error(_("Access company \"{0}\" in row #{1} is a group or doesn't exist.").format(v.company, i))
            if not v.secret_id:
                self._error(_("A valid access secret id in row #{0} is required.").format(i))
            if not is_valid_secret_id(v.secret_id):
                self._error(_("Access secret id in row #{0} is invalid.").format(i))
            if not v.secret_key:
                self._error(_("A valid access secret key in row #{0} is required.").format(i))
            if not is_valid_secret_key(v.secret_key):
                self._error(_("Access secret key in row #{0} is invalid.").format(i))
    
    
    def _error(self, msg):
        from erpnext_gocardless_bank.libs import error
        
        error(msg, _(self.doctype))