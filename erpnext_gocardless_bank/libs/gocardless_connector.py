# ERPNext Gocardless Bank © 2023
# Author:  Ameen Ahmed
# Company: Level Up Marketing & Software Development Services
# Licence: Please refer to LICENSE file


import frappe
from frappe import _
from frappe.utils import (
    get_request_session,
    get_request_site_address,
    cstr
)

from .gocardless_api import GocardlessApi
from .gocardless_common import (
    error,
    log_error,
    log_info,
    to_json,
    parse_json
)


class GocardlessConnector:
    def __init__(self):
        self.token = {}
    
    
    def connect(self, secret_id, secret_key):
        if (
            not secret_id or not isinstance(secret_id, str) or
            not secret_key or not isinstance(secret_key, str)
        ):
            error(_("Gocardless secret id or key is invalid."), code="vyGE6QZB23")
            return None
        
        token = self._request(
            GocardlessApi.new_token,
            {
                "secret_id": secret_id,
                "secret_key": secret_key
            },
            auth=False
        )
        if not token or not isinstance(token, dict):
            error(_("Unable to connect to Gocardless."), code="GEgr6QZB23")
            return None
        
        if (
            not token.get("access", "") or
            not isinstance(token.get("access"), str) or
            not token.get("access_expires", "") or
            not isinstance(token.get("access_expires"), (str, int)) or
            not token.get("refresh", "") or
            not isinstance(token.get("refresh"), str) or
            not token.get("refresh_expires", "") or
            not isinstance(token.get("refresh_expires"), (str, int))
        ):
            error(_("Gocardless access token received is invalid."), code="n2SpB23MhB")
            return None
        
        self.token.update(token)
    
    
    def set_access(self, access_token):
        if not access_token or not isinstance(access_token, str):
            error(_("Gocardless access token is invalid."), code="pBhn2SB23M")
        
        self.token["access"] = access_token
    
    
    def get_access(self):
        return self.token
    
    
    def _request(self, uri, data=None, auth=True, is_list=False, method=None):
        _url = f"{GocardlessApi.url}{uri}"
        _data = to_json(data) if isinstance(data, dict) else None
        _method = method or ("POST" if _data else "GET")
        _post = True if _method == "POST" else False
        _headers = GocardlessApi.headers
        
        if auth or _post:
            if auth and not self.token:
                error(_("Gocardless access token is missing."), code="c6EecdXJtY")
                return None
            
            _headers = _headers.copy()
            if auth:
                _headers["Authorization"] = "Bearer " + self.token["access"]
            if _post:
                _headers.update(GocardlessApi.post_headers)
        
        def report_error(exc=None):
            nonlocal _url, _data, _method, _headers
            log = {
                "url": _url,
                "method": _method,
                "data": _data,
                "headers": _headers
            }
            if exc:
                log["exception"] = str(exc)
            log_error(log)
        
        try:
            request = get_request_session().request(
                _method, _url, data=_data, headers=_headers
            )
            status_code = request.status_code
            response = request.json()
        except Exception as exc:
            report_error(exc)
            error(str(exc), code="FhJphGe4Bx")
            return None
        
        response = parse_json(response)
        
        if status_code != 200 and status_code != 201:
            err = GocardlessApi.parse_error(response)
            log_error({"error": err, "data": response})
            if "list" not in err:
                error(err, False, "Me84LVAWHe")
            return err
        
        if (
            (not is_list and not isinstance(response, dict)) or
            (is_list and not isinstance(response, list))
        ):
            report_error()
            error(_("Gocardless API response received is invalid."), code="qFH28egKy9")
            return None
        
        return response
    
    
    def refresh(self, refresh_token):
        if not refresh_token or not isinstance(refresh_token, str):
            error(_("Gocardless refresh token is invalid."), code="Pn6P64PVnS")
            return None
        
        token = self._request(
            GocardlessApi.refresh_token,
            {"refresh": refresh_token},
            auth=False
        )
        if not token or not isinstance(token, dict):
            error(_("Unable to refresh Gocardless access token."), code="RzRRkD3xvD")
            return None
        
        if (
            not token.get("access", "") or
            not isinstance(token.get("access"), str) or
            not token.get("access_expires", "") or
            not isinstance(token.get("access_expires"), (str, int))
        ):
            error(_("Gocardless refreshed access token received is invalid."), code="B23Mhn2SpB")
            return None
        
        self.token.update(token)
    
    
    def get_banks(self, country=None, pay_option=False):
        return self._request(
            GocardlessApi.list_banks(country, pay_option),
            is_list=True
        )
    
    
    def get_bank_agreement(self, bank_id, transaction_total_days):
        data = self._request(
            GocardlessApi.bank_agreement,
            {
                "institution_id": bank_id,
                "max_historical_days": transaction_total_days or 90,
                "access_valid_for_days": 180,
                "access_scope": ["balances", "details", "transactions"]
            }
        )
        if "access_valid_for_days" not in data:
            log_info({
                "info": "Bank agreement data received is not valid",
                "data": data
            })
            data["access_valid_for_days"] = 180
        
        return data
    
    
    def get_bank_link(
        self, bank_id, reference_id, transaction_total_days, docname = None
    ):
        agreement = self.get_bank_agreement(bank_id, transaction_total_days)
        if "error" in agreement:
            return agreement
        
        lang = "en"
        try:
            lang = frappe.lang
        except Exception:
            try:
                lang = frappe.local.lang
            except Exception:
                lang = "en"
        
        redirect_url = get_request_site_address(True)
        redirect_url = f"{redirect_url}/app/gocardless-bank"
        if docname:
            redirect_url = f"{redirect_url}/{docname}"
        
        data = self._request(
            GocardlessApi.bank_link,
            {
                "institution_id": bank_id,
                "redirect": redirect_url,
                "reference": reference_id,
                "agreement": str(agreement["id"]),
                "user_language": str(lang).upper(),
            }
        )
        
        if "error" not in data:
            data["access_valid_for_days"] = agreement["access_valid_for_days"]
        
        return data
    
    
    def remove_bank_link(self, auth_id):
        return self._request(GocardlessApi.bank_accounts(auth_id), method="DELETE")
    
    
    def get_accounts(self, auth_id):
        data = self._request(GocardlessApi.bank_accounts(auth_id))
        if "error" in data:
            return data
        
        if "accounts" not in data:
            err = _("Bank requisition data received has no bank accounts.")
            log_error({"error": err, "data": data})
            error(err, code="n2Sp9b7MhB")
            return []
        
        accounts = parse_json(data["accounts"])
        if not isinstance(accounts, list):
            err = _("Bank accounts data received from requisition is invalid.")
            log_error({"error": err, "data": data})
            error(err, code="u6wMBMwkdZ")
            accounts = []
        
        elif not accounts:
            err = _("Bank accounts data received from requisition is empty.")
            log_error({"error": err, "data": data})
            error(err, code="P664PnPVnS")
        
        return accounts
    
    
    def get_account_data(self, account_id):
        data = self._request(GocardlessApi.account_data(account_id))
        if "error" in data:
            return data
        
        status = "Ready"
        if "status" in data:
            if isinstance(data["status"], str):
                if (
                    data["status"] in GocardlessApi.account_status or
                    data["status"].lower() in GocardlessApi.account_status_new
                ):
                    status = data["status"].title()
            
            elif isinstance(data["status"], dict):
                for k in data["status"].keys():
                    if k in GocardlessApi.account_status:
                        status = k.title()
                        break
                    elif cstr(k).lower() in GocardlessApi.account_status_new:
                        status = k.title()
                        break
        
        data["status"] = status
        return data
    
    
    def get_account_balances(self, account_id):
        data = self._request(GocardlessApi.account_balances(account_id))
        if "error" in data:
            return data
        
        balances = []
        if "balances" not in data:
            err = _("Bank account data received for {0} has no balances.").format(account_id)
            log_error({"error": err, "data": data})
            error(err, code="gcJf2neHNY")
            return balances
        
        balances_data = parse_json(data["balances"])
        if not isinstance(balances_data, list):
            err = _("Bank account balances received for {0} is invalid.").format(account_id)
            log_error({"error": err, "data": data})
            error(err, code="rWKYwfNA8A")
            return balances
        
        if not balances_data:
            err = _("Bank account balances received for {0} is empty.").format(account_id)
            log_error({"error": err, "data": data})
            error(err, code="YwfNArWK8A")
            return balances
        
        for bal in balances_data:
            if (
                not isinstance(bal, dict)
                or "balanceAmount" not in bal
                or not isinstance(bal["balanceAmount"], dict)
                or "amount" not in bal["balanceAmount"]
                or "currency" not in bal["balanceAmount"]
            ):
                err = _("Bank account balances data received is invalid.")
                log_error({"error": err, "data": data})
                error(err, code="2nmCTc8rKL")
                if balances:
                    balances.clear()
                break
            
            balances.append({
                "amount": bal["balanceAmount"]["amount"],
                "currency": bal["balanceAmount"]["currency"],
                "type": bal.get("balanceType", ""),
                "date": bal.get("referenceDate", ""),
            })
        
        return balances
    
    
    def get_account_details(self, account_id):
        data = self._request(GocardlessApi.account_details(account_id))
        if "error" in data:
            return data
        
        if "account" not in data:
            err = _("Bank account details received has no data.")
            log_error({"error": err, "data": data})
            error(err, code="re5UK56vVf")
            return {}
        
        details = parse_json(data["account"])
        if not isinstance(details, dict):
            err = _("Bank account details received is invalid.")
            log_error({"error": err, "data": data})
            error(err, code="AGgdGAFn7W")
            details = {}
        
        if not details:
            err = _("Bank account details received is empty.")
            log_error({"error": err, "data": data})
            error(err, code="GAdAGgFn7W")
        
        return details
    
    
    def get_account_transactions(self, account_id, date_from, date_to):
        data = self._request(
            GocardlessApi.account_transactions(account_id, date_from, date_to)
        )
        
        log_info({
            "account_id": account_id,
            "from_date": date_from,
            "to_date": date_to,
            "data": data
        })
        
        if "error" in data:
            return data
        
        if "transactions" not in data:
            err = _("Bank account transactions received for {0} has no data.").format(account_id)
            log_error({"error": err, "data": data})
            error(err, code="wnq5Z8rKHn")
            return None
        
        data = parse_json(data["transactions"])
        if not isinstance(data, dict):
            err = _("Bank account transactions received for {0} is invalid.").format(account_id)
            log_error({"error": err, "data": data})
            error(err, code="mD5GFRngsW")
            return None
        
        if not data:
            err = _("Bank account transactions received for {0} is empty.").format(account_id)
            log_error({"error": err, "data": data})
            error(err, code="gsWmD5GFRn")
            return None
        
        if not data.get("booked", "") and not data.get("pending", ""):
            err = _("Bank account transactions received for {0} has no booked and pending data.").format(account_id)
            log_error({"error": err, "data": data})
            error(err, False, "5ZMs5EQK37")
            return None
        
        return data
    
    
    def prepare_entries(self, data):
        return GocardlessApi.prepare_transactions(data)