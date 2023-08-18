# ERPNext Nordigen © 2023
# Author:  Ameen Ahmed
# Company: Level Up Marketing & Software Development Services
# Licence: Please refer to LICENSE file


import re

import frappe
from frappe import _
from frappe.model.document import Document

from erpnext_nordigen.libs.nordigen import error, clear_doc_cache


class NordigenSettings(Document):
    def validate(self):
        if (
            len(self.secret_id) != 36 or
            not re.match(
                r"([a-z0-9]{8})-([a-z0-9]{4})-([a-z0-9]{4})-([a-z0-9]{4})-([a-z0-9]{12})",
                self.secret_id,
                flags=re.I
            )
        ):
            error(_("Please provide a valid secret id."), False, "6Urrhq7EHX")
        
        if (
            len(self.secret_key) != 128 or
            not re.match(r"([a-z0-9]+)", self.secret_key, flags=re.I)
        ):
            error(_("Please provide a valid secret key."), False, "KrgqU2TDwE")
    
    def before_save(self):
        clear_doc_cache()