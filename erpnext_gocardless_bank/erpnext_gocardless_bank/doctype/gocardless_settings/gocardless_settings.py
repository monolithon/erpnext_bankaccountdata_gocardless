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
            self.flags.emit_change = 1
    
    
    def on_update(self):
        if self.flags.get("emit_change", 0):
            from erpnext_gocardless_bank import __production__
            
            from erpnext_gocardless_bank.libs import emit_status_changed
            
            emit_status_changed({
                "is_enabled": 1 if self._is_enabled else 0,
                "is_debug": 0 if __production__ else 1
            })
        
        self._clean_flags()
    
    
    @property
    def _is_enabled(self):
        return cint(self.enabled) > 0
    
    
    @property
    def _clean_bank(self):
        return cint(self.clean_bank_dt) > 0
    
    
    @property
    def _clean_bank_account(self):
        return cint(self.clean_bank_account_dt) > 0
    
    
    @property
    def _clean_bank_account_type(self):
        return cint(self.clean_bank_account_type_dt) > 0
    
    
    @property
    def _clean_bank_transaction(self):
        return cint(self.clean_bank_transaction_dt) > 0
    
    
    @property
    def _clean_currency(self):
        return cint(self.clean_currency_dt) > 0
    
    
    @property
    def _clean_supplier(self):
        return cint(self.clean_supplier_dt) > 0
    
    
    @property
    def _clean_customer(self):
        return cint(self.clean_customer_dt) > 0
    
    
    def _set_defaults(self):
        ign = "Ignore"
        if self.bank_account_type_exist_for_bank_account == ign:
            if self.bank_account_type_of_bank_account_is_empty != ign:
                self.bank_account_type_of_bank_account_is_empty = ign
            if self.bank_account_type_of_bank_account_doesnt_exist != ign:
                self.bank_account_type_of_bank_account_doesnt_exist = ign
            if self.default_bank_account_type_of_bank_account:
                self.default_bank_account_type_of_bank_account = None
            if self._clean_bank_account_type:
                self.clean_bank_account_type_dt = 0
        
        elif (
            (
                self.bank_account_type_of_bank_account_is_empty != ign or
                self.bank_account_type_of_bank_account_doesnt_exist not in (ign, "Add Bank Account Type")
            ) and not self.default_bank_account_type_of_bank_account
        ):
            from erpnext_gocardless_bank.libs import add_account_type
            
            name = add_account_type("Gocardless Bank Account")
            if name:
                self.default_bank_account_type_of_bank_account = name
            else:
                self._add_error(_("Unable to create default bank account type \"Gocardless Bank Account\"."))
        
        if self.supplier_exist_in_transaction == ign:
            if self.supplier_in_transaction_doesnt_exist != ign:
                self.supplier_in_transaction_doesnt_exist = ign
            if self.supplier_bank_account_exist_in_transaction != ign:
                self.supplier_bank_account_exist_in_transaction = ign
        
        if self.customer_exist_in_transaction == ign:
            if self.customer_in_transaction_doesnt_exist != ign:
                self.customer_in_transaction_doesnt_exist = ign
            if self.customer_bank_account_exist_in_transaction != ign:
                self.customer_bank_account_exist_in_transaction = ign
        
        if self._clean_bank and not self._clean_bank_account:
            self.clean_bank_account_dt = 1
        
        if (
            self._clean_bank_account and not self._clean_bank_account_type and
            self.bank_account_type_exist_for_bank_account != ign
        ):
            self.clean_bank_account_type_dt = 1
        
        if self._clean_bank_account and not self._clean_bank_transaction:
            self.clean_bank_transaction_dt = 1
        
        if (
            self._clean_currency and
            self.bank_account_currency_doesnt_exist == ign and
            self.bank_transaction_currency_doesnt_exist == ign
        ):
            self.clean_currency_dt = 0
        
        if (
            self._clean_supplier and (
                self.supplier_exist_in_transaction == ign or
                self.supplier_in_transaction_doesnt_exist == ign or
                not self._clean_bank_transaction
            )
        ):
            self.clean_supplier_dt = 0
        
        if (
            self._clean_customer and (
                self.customer_exist_in_transaction == ign or
                self.customer_in_transaction_doesnt_exist == ign or
                not self._clean_bank_transaction
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
        
        table = _("Gocardless Access")
        exist = companies_filter(
            [v.company for v in self.access if v.company],
            {"is_group": 0}
        )
        for i, v in enumerate(self.access):
            if not v.company:
                self._add_error(_("{0} - #{1}: A valid company is required.").format(table, i + 1))
            elif v.company not in exist:
                self._add_error(_("{0} - #{1}: Company \"{2}\" is a group or doesn't exist.").format(table, i + 1, v.company))
            if not v.secret_id:
                self._add_error(_("{0} - #{1}: A valid secret id is required.").format(table, i + 1))
            elif not is_valid_secret_id(v.secret_id):
                self._error(_("{0} - #{1}: Secret id is invalid.").format(table, i + 1))
            if not v.secret_key:
                self._add_error(_("{0} - #{1}: A valid secret key is required.").format(table, i + 1))
            elif not is_valid_secret_key(v.secret_key):
                self._add_error(_("{0} - #{1}: Secret key is invalid.").format(table, i + 1))
        
        self._throw_errors()
    
    
    def _clean_flags(self):
        keys = [
            "error_list",
            "emit_change"
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