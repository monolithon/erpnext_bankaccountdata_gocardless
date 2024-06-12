# ERPNext Gocardless Bank © 2024
# Author:  Ameen Ahmed
# Company: Level Up Marketing & Software Development Services
# Licence: Please refer to LICENSE file


import frappe
from frappe import _
from frappe.utils import (
    get_request_session,
    get_request_site_address,
    cstr,
    cint
)

from erpnext_gocardless_bank import __production__

from .api import Api


class Gocardless:
    _def_transaction_days = 90
    _def_access_valid_days = 180
    
    
    def __init__(self):
        self.access = None
        self.token = None
    
    
    @property
    def is_debug(self):
        return 0 if __production__ else 1
    
    
    # [Access]
    def connect(self, secret_id: str, secret_key: str):
        if (
            not secret_id or not isinstance(secret_id, str) or
            not secret_key or not isinstance(secret_key, str)
        ):
            err = _("Gocardless secret id or key is invalid.")
            self._log_error(err)
            return {"error": err}
        
        data = self._send(
            Api.new_token,
            {
                "secret_id": secret_id,
                "secret_key": secret_key
            },
            auth=False
        )
        if data is None or "error" in data:
            return data
        
        if (
            not data.get("access", "") or
            not isinstance(data["access"], str) or
            not data.get("access_expires", "") or
            not isinstance(data["access_expires"], (str, int)) or
            not data.get("refresh", "") or
            not isinstance(data["refresh"], str) or
            not data.get("refresh_expires", "") or
            not isinstance(data["refresh_expires"], (str, int))
        ):
            self._store_error({"error": "Invalid token received.", "data": data})
            err = _("Gocardless token received is invalid.")
            self._log_error(err)
            return {"error": err}
        
        self.access = data["access"]
        self.token = data
        return data
    
    
    # [Access]
    def set_access(self, token: str):
        if not token or not isinstance(token, str):
            self._log_error(_("Gocardless access token is invalid."))
        
        self.access = token
    
    
    # [Access]
    def get_token(self):
        return self.token
    
    
    # [Access]
    def refresh(self, token: str):
        if not token or not isinstance(token, str):
            self._log_error(_("Gocardless refresh token is invalid."))
            return None
        
        data = self._send(
            Api.refresh_token,
            {"refresh": token},
            auth=False
        )
        if data is None or "error" in data:
            return None
        
        if (
            not data.get("access", "") or
            not isinstance(data["access"], str) or
            not data.get("access_expires", "") or
            not isinstance(data["access_expires"], (str, int))
        ):
            self._store_error({"error": "Invalid refreshed token received.", "data": data})
            self._log_error(_("Gocardless refreshed access token received is invalid."))
            return None
        
        self.access = data["access"]
        self.token = data
    
    
    # [Bank]
    def get_banks(self, country: str=None, pay_option: int=0):
        data = self._send(Api.list_banks(country, pay_option), is_list=True)
        if data is None or "error" in data:
            return data
        
        if not data:
            self._store_error({"error": "Emply banks list received.", "data": data})
            err = _("Gocardless banks list received is empty.")
            self._log_error(err)
            return {"error": err}
        
        for v in data:
            if (
                not isinstance(v, dict) or
                not v.get("id", "") or
                not isinstance(v["id"], str) or
                not v.get("name", "") or
                not isinstance(v["name"], str)
            ):
                self._store_error({"error": "Invalid banks list received.", "data": data})
                err = _("Gocardless banks list received is invalid.")
                self._log_error(err)
                return {"error": err}
        
        keys = ["id", "name", "transaction_total_days", "logo"]
        for i in range(len(data)):
            data[i] = {k:data[i][k] for k in keys if k in data[i]}
            if cint(data[i].get(keys[2], 0)) < 1:
                data[i][keys[2]] = self._def_transaction_days
        
        if self.is_debug:
            data.insert(0, dict(zip(keys, [
                "SANDBOXFINANCE_SFIN0000",
                "Testing Sandbox Finance",
                self._def_transaction_days,
                "https://cdn-logos.gocardless.com/ais/SANDBOXFINANCE_SFIN0000.png"
            ])))
        
        return data
    
    
    # [Internal]
    def get_bank_agreement(self, bank_id: str, transaction_days: int=None):
        if not transaction_days or cint(transaction_days) < 1:
            transaction_days = self._def_transaction_days
        
        data = self._send(Api.bank_agreement, {
            "institution_id": bank_id,
            "max_historical_days": transaction_days,
            "access_valid_for_days": self._def_access_valid_days,
            "access_scope": ["balances", "details", "transactions"]
        })
        if data is None or "error" in data:
            return data
        
        if (
            not data.get("id", "") or
            not isinstance(data["id"], str) or
            not data.get("institution_id", "") or
            not isinstance(data["institution_id"], str)
        ):
            self._store_error({"error": "Invalid bank agreement data received.", "data": data})
            err = _("Gocardless bank agreement data received for bank id ({0}) is invalid.").format(bank_id)
            self._log_error(err)
            return {"error": err}
        
        if "access_valid_for_days" in data:
            data["access_valid_for_days"] = cint(data["access_valid_for_days"])
        
        if cint(data.get("access_valid_for_days", 0)) < 1:
            self._store_info({
                "info": "Bank agreement data received is missing or has invalid access valid days value.",
                "data": data
            })
            data["access_valid_for_days"] = self._def_access_valid_days
        
        return data
    
    
    # [Bank]
    def get_bank_link(self, docname: str, ref_id: str, bank_id: str, transaction_days: int=None):
        agreement = self.get_bank_agreement(bank_id, transaction_days)
        if not isinstance(agreement, dict) or "error" in agreement:
            return agreement
        
        redirect_url = get_request_site_address(True)
        redirect_url = f"{redirect_url}/app/gocardless-bank/{docname}"
        
        data = self._send(
            Api.bank_link,
            {
                "reference": ref_id,
                "institution_id": bank_id,
                "agreement": agreement["id"],
                "redirect": redirect_url,
                "user_language": self._user_lang()
            }
        )
        if data is None or "error" in data:
            return data
        
        if (
            not data.get("id", "") or
            not isinstance(data["id"], str) or
            not data.get("link", "") or
            not isinstance(data["link"], str)
        ):
            self._store_error({"error": "Invalid bank link data received.", "data": data})
            err = _("Gocardless bank link data received for bank id ({0}) is invalid.").format(bank_id)
            self._log_error(err)
            return {"error": err}
        
        data["auth_id"] = data.pop("id")
        data["auth_link"] = data.pop("link")
        data["auth_expiry"] = agreement["access_valid_for_days"]
        return data
    
    
    # [Bank]
    def remove_bank_link(self, auth_id: str):
        data = self._send(Api.bank_accounts(auth_id), method="DELETE")
        return data if data and "error" in data else None
    
    
    # [Bank Account]
    def get_accounts(self, auth_id: str):
        data = self._send(Api.bank_accounts(auth_id))
        if data is None or "error" in data:
            return data
        
        if "accounts" not in data:
            self._store_error({"error": "Invalid bank accounts list received.", "data": data})
            self._log_error(_("Gocardless bank accounts list received is invalid."))
            return []
        
        accounts = self._parse_json(data["accounts"])
        if not isinstance(accounts, list):
            self._store_error({"error": "Invalid bank accounts list received.", "data": data})
            self._log_error(_("Gocardless bank accounts list received is invalid."))
            accounts = []
        
        elif not accounts:
            self._store_error({"error": "Empty bank accounts list received.", "data": data})
            self._log_error(_("Gocardless bank accounts list received is empty."))
        
        return accounts
    
    
    # [Bank Account]
    def get_account_data(self, account_id: str):
        data = self._send(Api.account_data(account_id))
        if data is None or "error" in data:
            return data
        
        if (
            not data.get("id", "") or
            not isinstance(data["id"], str)
        ):
            self._store_error({"error": "Invalid bank account data received.", "account_id": account_id, "data": data})
            self._log_error(_("Gocardless bank account data received for bank account id ({0}) is invalid.").format(account_id))
            return None
        
        status = "Ready"
        if "status" not in data:
            self._store_info({"info": "Bank account data received is missing status value.", "data": data})
        else:
            if isinstance(data["status"], str):
                if (
                    data["status"] in Api.account_status["old"] or
                    data["status"].lower() in Api.account_status["new"]
                ):
                    status = data["status"].title()
            
            elif isinstance(data["status"], dict):
                for k in data["status"].keys():
                    if (
                        k in Api.account_status["old"] or
                        cstr(k).lower() in Api.account_status["new"]
                    ):
                        status = cstr(k).title()
                        break
            
            else:
                self._store_info({"info": "Bank account data received has invalid status value.", "data": data})
        
        data["status"] = status
        return data
    
    
    # [Bank Account]
    def get_account_balances(self, account_id: str):
        data = self._send(Api.account_balances(account_id))
        if data is None or "error" in data:
            return data
        
        balances = []
        if "balances" not in data:
            self._store_error({"error": "Invalid bank account balances received.", "account_id": account_id, "data": data})
            self._log_error(_("Gocardless bank account balances received for bank account id ({0}) is invalid.").format(account_id))
            return balances
        
        balances_data = self._parse_json(data["balances"])
        if not isinstance(balances_data, list):
            self._store_error({"error": "Invalid bank account balances received.", "account_id": account_id, "data": data})
            self._log_error(_("Gocardless bank account balances received for bank account id ({0}) is invalid.").format(account_id))
            return balances
        
        if not balances_data:
            self._store_error({"error": "Empty bank account balances received.", "account_id": account_id, "data": data})
            self._log_error(_("Gocardless bank account balances received for bank account id ({0}) is empty.").format(account_id))
            return balances
        
        for v in balances_data:
            if (
                not isinstance(v, dict) or
                not v.get("balanceAmount", "") or
                not isinstance(v["balanceAmount"], dict) or
                "amount" not in v["balanceAmount"] or
                "currency" not in v["balanceAmount"] or
                not v.get("balanceType", "")
            ):
                self._store_error({"error": "Invalid bank account balances list received.", "account_id": account_id, "data": data})
                self._log_error(_("Gocardless bank account balances list received for bank account id ({0}) is invalid.").format(account_id))
                if balances:
                    balances.clear()
                break
            
            balance_type = Api.account_balance_types.get(v["balanceType"], "")
            if not balance_type:
                balance_type = v["balanceType"]
                self._store_info({"info": "Balance type not recorded.", "data": v})
            
            balances.append({
                "type": balance_type,
                "amount": v["balanceAmount"]["amount"],
                "currency": v["balanceAmount"]["currency"],
                "inc_limit": v.get("creditLimitIncluded", ""),
                "last_change": v.get("lastChangeDateTime", ""),
                "date": v.get("referenceDate", ""),
                "reqd": 1 if balance_type in Api.reqd_account_balance_types else 0
            })
        
        types_vals = list(Api.account_balance_types.values())
        def data_sorter(val):
            nonlocal types_vals
            
            if val["type"] not in types_vals:
                idx = 100
            else:
                idx = types_vals.index(val["type"])
            return idx
        
        balances = sorted(balances, key=data_sorter)
        return balances
    
    
    # [Bank Account]
    def get_account_details(self, account_id: str):
        data = self._send(Api.account_details(account_id))
        if data is None or "error" in data:
            return data
        
        if "account" not in data:
            self._store_error({"error": "Invalid bank account details received.", "account_id": account_id, "data": data})
            self._log_error(_("Gocardless bank account details received for bank account id ({0}) is invalid.").format(account_id))
            return {}
        
        details = self._parse_json(data["account"])
        if not isinstance(details, dict):
            self._store_error({"error": "Invalid bank account details received.", "account_id": account_id, "data": data})
            self._log_error(_("Gocardless bank account details received for bank account id ({0}) is invalid.").format(account_id))
            details = {}
        
        elif not details:
            self._store_error({"error": "Empty bank account details received.", "account_id": account_id, "data": data})
            self._log_error(_("Gocardless bank account details received for bank account id ({0}) is empty.").format(account_id))
        
        return details
    
    
    # [Bank Transaction]
    def get_account_transactions(self, account_id: str, date_from: str=None, date_to: str=None):
        data = self._send(Api.account_transactions(account_id, date_from, date_to))
        if data is None or "error" in data:
            return data
        
        if "transactions" not in data:
            self._store_error({
                "error": "Invalid bank account transactions received.", "account_id": account_id,
                "date": [date_from, date_to], "data": data
            })
            self._log_error(_("Gocardless bank account transactions received for bank account id ({0}) is invalid.").format(account_id))
            return None
        
        data = self._parse_json(data["transactions"])
        if not isinstance(data, dict):
            self._store_error({
                "error": "Invalid bank account transactions received.", "account_id": account_id,
                "date": [date_from, date_to], "data": data
            })
            self._log_error(_("Gocardless bank account transactions received for bank account id ({0}) is invalid.").format(account_id))
            return None
        
        if not data:
            self._store_error({
                "error": "Empty bank account transactions received.", "account_id": account_id,
                "date": [date_from, date_to], "data": data
            })
            self._log_error(_("Gocardless bank account transactions received for bank account id ({0}) is empty.").format(account_id))
            return None
        
        if not data.get("booked", "") and not data.get("pending", ""):
            self._store_error({
                "error": "No booked and pending bank account transactions received.", "account_id": account_id,
                "date": [date_from, date_to], "data": data
            })
            self._log_error(_("Gocardless bank account transactions received for bank account id ({0}) has no booked and pending data.").format(account_id))
            return None
        
        return data
    
    
    # [Bank Transaction]
    @staticmethod
    def prepare_entries(data: list|dict):
        return Api.prepare_transactions(data)
    
    
    def _send(self, uri: str, data: dict=None, auth: bool=True, is_list: bool=False, method: str=None):
        url = f"{Api.url}{uri}"
        if data:
            from .common import to_json
            
            data = to_json(data)
        else:
            data = None
        if not method:
            method = "POST" if data else "GET"
        is_post = True if method == "POST" else False
        is_delete = True if method == "DELETE" else False
        headers = Api.headers
        
        if auth or is_post:
            if auth and not self.access:
                err = _("Gocardless access token is missing.")
                self._log_error(err)
                return {"error": err}
            
            headers = headers.copy()
            if auth:
                headers["Authorization"] = "Bearer " + self.access
            if is_post:
                headers.update(Api.post_headers)
        
        try:
            request = get_request_session().request(
                method, url, data=data, headers=headers
            )
            status = int(request.status_code)
            response = request.json()
        except Exception as exc:
            self._store_error({
                "error": "Request failed. {0}".format(str(exc)),
                "url": url,
                "method": method,
                "data": data
            })
            err = _("Gocardless request failed. {0}").format(str(exc))
            self._log_error(err)
            return {"error": err}
        
        response = self._parse_json(response)
        if status not in Api.valid_status_codes:
            err = self._report_error(response)
            return {"error": err}
        
        if is_delete:
            return None
        
        if (
            (not is_list and not isinstance(response, dict)) or
            (is_list and not isinstance(response, list))
        ):
            self._store_error({
                "error": "Invalid response received.",
                "url": url,
                "method": method,
                "data": data,
                "response": response
            })
            err = _("Gocardless response received is invalid.")
            self._log_error(err)
            return {"error": err}
        
        return response
    
    
    @staticmethod
    def _report_error(response):
        error = Api.parse_error(response)
        if isinstance(error, dict) and "error" in error:
            err = error.pop("error").strip(".") + "."
        elif isinstance(error, list):
            err = []
            for i in range(len(error)):
                v = error.pop(0)
                if isinstance(v, dict) and "error" in v:
                    err.append(v.pop("error").strip(".") + ".")
            
            err = "\n".join(err) if err else None
        else:
            err = None
        
        if not err:
            err = _("Gocardless error reported has invalid error data.")
        
        Gocardless._log_error(err)
        Gocardless._store_error({"error": err, "data": response})
        return err
    
    
    @staticmethod
    def _user_lang():
        try:
            lang = cstr(frappe.lang)
        except Exception:
            try:
                lang = cstr(frappe.local.lang)
            except Exception:
                lang = None
        
        if not lang:
            lang = "en"
        
        return lang.upper()
    
    
    @staticmethod
    def _parse_json(data):
        from .common import parse_json
        
        return parse_json(data, data)
    
    
    @staticmethod
    def _log_error(data):
        from .common import log_error
        
        log_error(data)
    
    
    @staticmethod
    def _store_error(data):
        from .common import store_error
        
        store_error(data)
    
    
    @staticmethod
    def _store_info(data):
        from .common import store_info
        
        store_info(data)