# ERPNext Gocardless Bank © 2024
# Author:  Ameen Ahmed
# Company: Level Up Marketing & Software Development Services
# Licence: Please refer to LICENSE file


class Api:
    url = "https://bankaccountdata.gocardless.com/api/v2/"
    headers = {"Accept": "application/json"}
    post_headers = {"Content-Type": "application/json"}
    valid_status_codes = [200, 201]
    
    
    new_token = "token/new/"
    refresh_token = "token/refresh/"
    
    
    @staticmethod
    def list_banks(country):
        uri = "institutions/"
        if country:
            uri = f"{uri}?country={country}"
        
        return uri
    
    
    bank_agreement = "agreements/enduser/"
    bank_link = "requisitions/"
    
    
    @staticmethod
    def bank_accounts(auth_id):
        return f"requisitions/{auth_id}/"
    
    
    account_status = {
        "new": [
            "enabled",
            "deleted",
            "blocked"
        ],
        "old": [
            "DISCOVERED",
            "PROCESSING",
            "ERROR",
            "EXPIRED",
            "READY",
            "SUSPENDED"
        ]
    }
    
    
    @staticmethod
    def account_data(account_id):
        return f"accounts/{account_id}/"
    
    
    @staticmethod
    def account_balances(account_id):
        return f"accounts/{account_id}/balances/"
    
    
    account_balance_types = {
        "openingAvailable": "opening",
        "openingBooked": "opening_booked",
        "closingAvailable": "closing",
        "closingBooked": "closing_booked",
        "forwardAvailable": "forward",
        "interimAvailable": "temp_balance",
        "interimBooked": "temp_booked",
        "expected": "day_balance",
        "information": "info_balance",
        "nonInvoiced": "uninvoiced",
        "previouslyClosedBooked": "prev_closing_booked"
    }
    
    
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
            qry = "&".join(qry)
            uri = f"{uri}?{qry}"
        
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
        "account_info": {
            "iban": "iban",
            "bban": "account",
            "pan": "account_no",
            "maskedPan": "account_no",
            "currency": "currency"
        },
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
        from .common import to_json
        
        for entry in transactions:
            info = {}
            for k in list(entry):
                ek = "main"
                if k in Api.transactions[ek]:
                    entry[Api.transactions[ek][k]] = entry.pop(k)
                    continue
                
                ek = "date"
                if k in Api.transactions[ek]:
                    val = entry.pop(k)
                    if ek not in entry and val:
                        entry[ek] = val
                    
                    if (
                        ek in entry and val and
                        k in Api.transactions["keys"]
                    ):
                        info[Api.transactions["keys"][k]] = val
                    
                    continue
                
                ek = "description"
                if k in Api.transactions[ek]:
                    val = entry.pop(k)
                    if ek not in entry and val:
                        if isinstance(val, list):
                            val = val.pop(0)
                        if isinstance(val, str) and val:
                            entry[ek] = val
                    
                    if (
                        ek in entry and val and
                        k in Api.transactions["keys"]
                    ):
                        info[Api.transactions["keys"][k]] = val
                    
                    continue
                
                if k in Api.transactions["merge"]:
                    val = entry.pop(k)
                    if val:
                        entry.update(val)
                    
                    continue
                
                ek = "information"
                if k in Api.transactions[ek]:
                    val = entry.pop(k)
                    if val:
                        if k == "currencyExchange" and isinstance(val, dict):
                            val = Api.prepare_currency_exchange(val)
                        
                        info[Api.transactions[ek][k]] = val
                    
                    continue
                
                ek = "supplier"
                if k in Api.transactions[ek]:
                    val = entry.pop(k)
                    if ek not in entry:
                        entry[ek] = {}
                    
                    nk = k[8:].lower()
                    if not isinstance(val, dict):
                        entry[ek][nk] = val
                    elif val:
                        cnt = 0
                        for x in Api.transactions["account_info"]:
                            z = Api.transactions["account_info"][x]
                            if not entry[ek].get(z, ""):
                                entry[ek][z] = val.get(x, "")
                            if entry[ek].get(z, ""):
                                cnt = 1
                        
                        if not cnt:
                            entry[ek][nk] = next(iter(val.values()))
                        if not entry[ek].get("account", "") and entry[ek].get("iban", ""):
                            entry[ek]["account"] = entry[ek]["iban"]
                    
                    continue
                
                ek = "customer"
                if k in Api.transactions[ek]:
                    val = entry.pop(k)
                    if ek not in entry:
                        entry[ek] = {}
                    
                    nk = k[6:].lower()
                    if not isinstance(val, dict):
                        entry[ek][nk] = val
                    elif val:
                        cnt = 0
                        for x in Api.transactions["account_info"]:
                            z = Api.transactions["account_info"][x]
                            if not entry[ek].get(z, ""):
                                entry[ek][z] = val.get(x, "")
                            if entry[ek].get(z, ""):
                                cnt = 1
                        
                        if not cnt:
                            entry[ek][nk] = next(iter(val.values()))
                        if not entry[ek].get("account", "") and entry[ek].get("iban", ""):
                            entry[ek]["account"] = entry[ek]["iban"]
            
            entry["information"] = to_json(info, "", True)
        
        return transactions
    
    
    @staticmethod
    def prepare_currency_exchange(entry):
        for k in list(entry):
            val = entry.pop(k)
            if val and k in Api.transactions["exchange_keys"]:
                entry[Api.transactions["exchange_keys"][k]] = val
        
        return entry
    
    
    errors = {
        "list": {
            "many": [
                "access_scope",
                "agreement",
                "redirect"
            ],
            "single": [
                "max_historical_days",
                "access_valid_for_days"
            ],
            "str": [
                "redirect",
                "institution_id"
            ]
        },
        "dict": {
            "group": [
                "institution_id",
                "agreement",
                "reference",
                "user_language",
                "ssn",
                "account_selection"
            ]
        }
    }
    
    
    @staticmethod
    def parse_error(data):
        if data and isinstance(data, dict):
            if "summary" in data and "detail" in data:
                err = {"error": str(data.pop("summary")).strip(".") + "."}
                if err["error"] != data["detail"]:
                    err["detail"] = str(data.pop("detail")).strip(".") + "."
                return err
            
            if (
                "id" in data and "aspsp_identifier" in data and
                "status" in data and data["status"] == "ERROR"
            ):
                return {"error": "Account state doesn't support this operation."}
            
            for k in Api.errors["list"]["many"]:
                if data.get(k, "") and isinstance(data[k], list):
                    return [Api.parse_error(v) for v in data.pop(k)]
            
            for k in Api.errors["list"]["single"]:
                if data.get(k, "") and isinstance(data[k], list):
                    return Api.parse_error(data.pop(k)[0])
            
            for k in Api.errors["list"]["str"]:
                if (
                    data.get(k, "") and isinstance(data[k], list) and
                    isinstance(data[k][0], str) and data[k][0]
                ):
                    return {"error": str(data.pop(k)[0]).strip(".") + "."}
            
            for k in Api.errors["dict"]["group"]:
                if (
                    data.get(k, "") and isinstance(data[k], dict) and
                    "summary" in data[k] and "detail" in data[k]
                ):
                    return Api.parse_error(data.pop(k))
        
        return {"error": "Response received is invalid."}