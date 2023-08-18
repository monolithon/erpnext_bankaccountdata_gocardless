# ERPNext Nordigen © 2023
# Author:  Ameen Ahmed
# Company: Level Up Marketing & Software Development Services
# Licence: Please refer to LICENSE file


from .nordigen_common import to_json, to_pretty_json


class NordigenApi:
    url = "https://ob.gocardless.com/api/v2/"
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json"
    }
    
    
    new_token = "token/new/"
    refresh_token = "token/refresh/"
    
    
    @staticmethod
    def list_banks(country=None, pay_option=False):
        qry = []
        if country:
            qry.append(f"country={country}")
        if pay_option:
            qry.append("payments_enabled=true")
        
        qry_str = "?" + ("&".join(qry)) if qry else ""
        return f"institutions/{qry_str}"
    
    
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
        qry = []
        if date_from:
            qry.append(f"date_from={date_from}")
        if date_to:
            qry.append(f"date_to={date_to}")
        
        qry = "?" + ("&".join(qry)) if qry else ""
        
        return f"accounts/{account_id}/transactions/{qry}"
    
    
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
            
            for k in list(entry):
                ek = "main"
                if k in NordigenApi.transactions[ek]:
                    entry[NordigenApi.transactions[ek][k]] = entry[k]
                    del entry[k]
                    continue
                
                ek = "date"
                if k in NordigenApi.transactions[ek]:
                    if ek not in entry and entry[k]:
                        entry[ek] = entry[k]
                    
                    if (
                        ek in entry and entry[k] and
                        k in NordigenApi.transactions["keys"]
                    ):
                        info[NordigenApi.transactions["keys"][k]] = entry[k]
                    
                    del entry[k]
                    continue
                
                ek = "description"
                if k in NordigenApi.transactions[ek]:
                    if ek not in entry and entry[k]:
                        if isinstance(entry[k], list):
                            entry[k] = entry[k].pop(0)
                        if isinstance(entry[k], str) and entry[k]:
                            entry[ek] = entry[k]
                    
                    if (
                        ek in entry and entry[k] and
                        k in NordigenApi.transactions["keys"]
                    ):
                        info[NordigenApi.transactions["keys"][k]] = entry[k]
                    
                    del entry[k]
                    continue
                
                if k in NordigenApi.transactions["merge"]:
                    if entry[k]:
                        entry.update(entry[k])
                    del entry[k]
                    continue
                
                ek = "information"
                if k in NordigenApi.transactions[ek]:
                    if entry[k]:
                        if k == "currencyExchange" and isinstance(entry[k], dict):
                            entry[k] = NordigenApi.prepare_currency_exchange(entry[k])
                        
                        info[NordigenApi.transactions[ek][k]] = entry[k]
                    
                    del entry[k]
                    continue
                
                ek = "supplier"
                if k in NordigenApi.transactions[ek]:
                    if ek not in entry:
                        entry[ek] = {}
                    
                    nk = k[8:].lower()
                    entry[ek][nk] = entry[k]
                    
                    if isinstance(entry[k], dict):
                        if entry[k]:
                            entry[ek][nk] = next(iter(entry[k].values()))
                        else:
                            del entry[ek][nk]
                    
                    del entry[k]
                    continue
                
                ek = "customer"
                if k in NordigenApi.transactions[ek]:
                    if ek not in entry:
                        entry[ek] = {}
                    
                    nk = k[6:].lower()
                    entry[ek][nk] = entry[k]
                    
                    if isinstance(entry[k], dict):
                        if entry[k]:
                            entry[ek][nk] = next(iter(entry[k].values()))
                        else:
                            del entry[ek][nk]
                    
                    del entry[k]
            
            entry["information"] = to_pretty_json(info, "")
        
        return transactions
    
    
    @staticmethod
    def prepare_currency_exchange(entry):
        for k in list(entry):
            if entry[k] and k in NordigenApi.transactions["exchange_keys"]:
                entry[NordigenApi.transactions["exchange_keys"][k]] = entry[k]
            del entry[k]
        
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
        
        for k in NordigenApi.errors["list"]:
            if (
                k in data and isinstance(data[k], list) and
                data[k] and isinstance(data[k][0], dict)
            ):
                return {
                    "error": 1,
                    "list": [NordigenApi.parse_error(v) for v in data[k]]
                }
        
        parsed = False
        for k in NordigenApi.errors["main"]:
            if k in data and isinstance(data[k], list):
                data = {"detail": to_json(data)}
                parsed = True
                break
        
        if not parsed:
            for k in NordigenApi.errors["fields"]:
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