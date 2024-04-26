# ERPNext Gocardless Bank © 2023
# Author:  Ameen Ahmed
# Company: Level Up Marketing & Software Development Services
# Licence: Please refer to LICENSE file


from .gocardless_common import to_json, to_pretty_json


class GocardlessApi:
    url = "https://bankaccountdata.gocardless.com/api/v2/"
    headers = {
        "Accept": "application/json"
    }
    post_headers = {
        "Content-Type": "application/json"
    }
    
    
    new_token = "token/new/"
    refresh_token = "token/refresh/"
    
    
    @staticmethod
    def list_banks(country, pay_option):
        uri = "institutions/"
        qry = []
        if country:
            qry.append(f"country={country}")
        if pay_option:
            qry.append("payments_enabled=true")
        if qry:
            uri = uri + "?" + "&".join(qry)
        return uri
    
    
    bank_agreement = "agreements/enduser/"
    bank_link = "requisitions/"
    
    
    @staticmethod
    def bank_accounts(auth_id):
        return f"requisitions/{auth_id}/"
    
    
    account_status_new = ["enabled", "deleted", "blocked"]
    account_status = ["DISCOVERED", "PROCESSING", "ERROR", "EXPIRED", "READY", "SUSPENDED"]
    
    
    @staticmethod
    def account_data(account_id):
        return f"accounts/{account_id}/"
    
    
    @staticmethod
    def account_balances(account_id):
        return f"accounts/{account_id}/balances/"
    
    
    @staticmethod
    def account_details(account_id):
        return f"accounts/{account_id}/details/"
    
    
    @staticmethod
    def account_transactions(account_id, date_from=None, date_to=None):
        uri = f"accounts/{account_id}/transactions/"
        qry = []
        if date_from:
            qry.append(f"date_from={date_from}")
        if date_to:
            qry.append(f"date_to={date_to}")
        if qry:
            uri = uri + "?" + "&".join(qry)
        return uri
    
    
    transactions = {
        "main": {
            "bankTransactionCode": "reference_number",
            "transactionId": "transaction_id",
        },
        "date": [
            "bookingDate",
            "bookingDateTime",
            "valueDate",
            "valueDateTime"
        ],
        "description": [
            "remittanceInformationStructured",
            "remittanceInformationStructuredArray",
            "remittanceInformationUnstructured",
            "remittanceInformationUnstructuredArray"
        ],
        "merge": ["transactionAmount"],
        "information": {
            "endToEndId": "End To End ID",
            "mandateId": "Mandate ID",
            "checkId": "Check ID",
            "internalTransactionId": "Internal Transaction ID",
            "entryReference": "Entry Reference",
            "proprietaryBankTransactionCode": "Proprietary Bank Transaction Code",
            "purposeCode": "Purpose Code",
            "currencyExchange": "Currency Exchange",
            "additionalInformation": "Additional Info",
            "remittanceInformationStructured": "Remittance Info",
            "remittanceInformationStructuredArray": "Remittance Info Array",
            "remittanceInformationUnstructured": "Unstructured Remittance Info",
            "remittanceInformationUnstructuredArray": "Unstructured Remittance Info Array"
        },
        "supplier": [
            "creditorId",
            "creditorName",
            "creditorAccount",
            "ultimateCreditor"
        ],
        "customer": [
            "debtorName",
            "debtorAccount",
            "ultimateDebtor"
        ],
        "keys": {
            "bookingDate": "Booking Date",
            "bookingDateTime": "Booking DateTime",
            "valueDate": "Value Date",
            "valueDateTime": "Value DateTime"
        },
        "exchange_keys": {
            "sourceCurrency": "From",
            "exchangeRate": "Rate",
            "unitCurrency": "Unit",
            "targetCurrency": "To",
            "quotationDate": "Date",
            "contractIdentification": "Ref. ID"
        }
    }
    
    
    @staticmethod
    def prepare_transactions(transactions):
        for entry in transactions:
            info = {}
            for k in entry.keys():
                ek = "main"
                if k in GocardlessApi.transactions[ek]:
                    entry[GocardlessApi.transactions[ek][k]] = entry.pop(k)
                    continue
                
                ek = "date"
                if k in GocardlessApi.transactions[ek]:
                    val = entry.pop(k)
                    if ek not in entry and val:
                        entry[ek] = val
                    
                    if (
                        ek in entry and val and
                        k in GocardlessApi.transactions["keys"]
                    ):
                        info[GocardlessApi.transactions["keys"][k]] = val
                    
                    continue
                
                ek = "description"
                if k in GocardlessApi.transactions[ek]:
                    val = entry.pop(k)
                    if ek not in entry and val:
                        if isinstance(val, list):
                            val = val.pop(0)
                        if isinstance(val, str) and val:
                            entry[ek] = val
                    
                    if (
                        ek in entry and val and
                        k in GocardlessApi.transactions["keys"]
                    ):
                        info[GocardlessApi.transactions["keys"][k]] = val
                    
                    continue
                
                if k in GocardlessApi.transactions["merge"]:
                    val = entry.pop(k)
                    if val:
                        entry.update(val)
                    
                    continue
                
                ek = "information"
                if k in GocardlessApi.transactions[ek]:
                    val = entry.pop(k)
                    if val:
                        if k == "currencyExchange" and isinstance(val, dict):
                            val = GocardlessApi.prepare_currency_exchange(val)
                        
                        info[GocardlessApi.transactions[ek][k]] = val
                    
                    continue
                
                ek = "supplier"
                if k in GocardlessApi.transactions[ek]:
                    val = entry.pop(k)
                    if ek not in entry:
                        entry[ek] = {}
                    
                    nk = k[8:].lower()
                    entry[ek][nk] = val
                    
                    if isinstance(val, dict):
                        if val:
                            entry[ek][nk] = next(iter(val.values()))
                        else:
                            del entry[ek][nk]
                    
                    continue
                
                ek = "customer"
                if k in GocardlessApi.transactions[ek]:
                    val = entry.pop(k)
                    if ek not in entry:
                        entry[ek] = {}
                    
                    nk = k[6:].lower()
                    entry[ek][nk] = val
                    
                    if isinstance(val, dict):
                        if val:
                            entry[ek][nk] = next(iter(val.values()))
                        else:
                            del entry[ek][nk]
            
            entry["information"] = to_pretty_json(info, "")
        
        return transactions
    
    
    @staticmethod
    def prepare_currency_exchange(entry):
        for k in list(entry):
            val = entry.pop(k)
            if val and k in GocardlessApi.transactions["exchange_keys"]:
                entry[GocardlessApi.transactions["exchange_keys"][k]] = val
        
        return entry
    
    
    errors = {
        "list": ["access_scope", "agreement", "redirect"],
        "main": ["institution_id", "redirect"],
        "fields": [
            "institution_id",
            "max_historical_days",
            "access_valid_for_days",
            "agreement",
            "user_language",
            "reference",
            "ssn",
            "account_selection",
        ]
    }
    
    
    @staticmethod
    def parse_error(data):
        err = {
            "error": 1,
            "title": "Response Error",
            "message": "The response received is invalid.",
        }
        if not isinstance(data, dict):
            return err
        
        for k in GocardlessApi.errors["list"]:
            if (
                k in data and isinstance(data[k], list) and
                data[k] and isinstance(data[k][0], dict)
            ):
                return {
                    "error": 1,
                    "list": [GocardlessApi.parse_error(v) for v in data[k]]
                }
        
        parsed = False
        for k in GocardlessApi.errors["main"]:
            if k in data and isinstance(data[k], list):
                data = {"detail": to_json(data)}
                parsed = True
                break
        
        if not parsed:
            for k in GocardlessApi.errors["fields"]:
                if k in data and isinstance(data[k], dict):
                    data = data[k]
                    break
        
        if "summary" in data:
            err["title"] = data["summary"]
            if "type" in data:
                err["title"] = data["type"] + " - " + err["title"]
        elif "id" in data and "status" in data:
            err["title"] = "Account state error"
            err["message"] = "Account state does not support this operation."
        
        if "detail" in data:
            err["message"] = data["detail"]
        elif "country" in data:
            err["message"] = data["country"][0]
        
        return err