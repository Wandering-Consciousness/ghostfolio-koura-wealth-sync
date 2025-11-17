import json
import re
from datetime import datetime
from typing import Optional, Dict, List
from dateutil.relativedelta import relativedelta
import yaml
import os

import requests

# Create logger
import logging
logger = logging.getLogger(__name__)


def format_existing_act(act: dict, symbol_type: str = "symbol") -> dict:
    symbol = act.get("SymbolProfile", {symbol_type: ""}).get(symbol_type)

    if symbol is None or len(symbol) == 0:
        logger.warning("Could not find nested symbol type %s for activity %s: %s",
                       symbol_type, act["id"], act.get("SymbolProfile"))
        symbol = act.get("symbol", "")

    return {
        "accountId": act["accountId"],
        "date": act["date"][0:18],
        "fee": abs(float(act["fee"])),
        "quantity": abs(float(act["quantity"])),
        "symbol": symbol,
        "type": act["type"],
        "unitPrice": act["unitPrice"]
    }


def format_new_act(act: dict, symbol_type: str = "symbol") -> dict:
    return {
        "accountId": act["accountId"],
        "date": act["date"][0:18],
        "fee": abs(float(act["fee"])),
        "quantity": abs(float(act["quantity"])),
        "symbol": act.get(symbol_type, ""),
        "type": act["type"],
        "unitPrice": act["unitPrice"]
    }


def is_act_present(new_act, existing_acts, synced_acts_ids: set):
    # Precise comparison using the transaction ID
    comment = new_act.get("comment")
    if comment is not None:
        # Extract the transactionId from the comment using regular expressions
        match = re.search(r"transactionId=([^|]+)", comment)
        if match:
            transaction_id = match.group(1)
            if transaction_id in synced_acts_ids:
                return True

    # Legacy comparison
    for existing_act in existing_acts:
        formatted_act = format_existing_act(existing_act)
        formatted_new_act = format_new_act(new_act)
        if formatted_act == formatted_new_act:
            return True
    return False


def get_diff(old_acts, new_acts):
    diff = []
    synced_acts_ids = set()
    for old_act in old_acts:
        comment = old_act.get("comment")
        if comment is not None:
            # Extract the transactionId from the comment
            match = re.search(r"transactionId=([^|]+)", comment)
            if match:
                transaction_id = match.group(1)
                synced_acts_ids.add(transaction_id)

    for new_act in new_acts:
        if not is_act_present(new_act, old_acts, synced_acts_ids):
            diff.append(new_act)
    return diff


def generate_chunks(lst, n):
    for i in range(0, len(lst), n):
        yield lst[i:i + n]


class SyncKoura:
    # Allocation field mapping (from API to fund code)
    ALLOCATION_MAPPING = {
        "cash": "810001",
        "fixedInterest": "810002",
        "nzEquities": "810003",
        "usEquities": "810004",
        "eafeEquities": "810005",
        "emEquities": "810006",
        "crypto": "810007",
        "cleanEnergy": "810008",
        "property": "810009",
        "strategicGrowth": "810010",
    }

    def __init__(self, ghost_host, koura_username, koura_password, ghost_key, ghost_token,
                 koura_account_id, ghost_account_name, ghost_currency, ghost_koura_platform, mapping_file='mapping.yaml'):
        self.account_id: Optional[str] = None
        if ghost_token == "" and ghost_key != "":
            self.ghost_token = self.create_ghost_token(ghost_host, ghost_key)
        else:
            self.ghost_token = ghost_token

        if self.ghost_token is None or self.ghost_token == "":
            logger.info("No bearer token provided, closing now")
            raise Exception("No bearer token provided")

        self.ghost_host = ghost_host
        self.koura_account_id = koura_account_id
        self.ghost_account_name = ghost_account_name
        self.ghost_currency = ghost_currency
        self.koura_username = koura_username
        self.koura_password = koura_password
        self.koura_platform = ghost_koura_platform
        self.koura_token = None
        self.koura_user_tag = "a8a4a355-8722-4a24-b24c-115b0470cdef"  # Required header

        # Initialize fund mapping - use Ghostfolio GF_ prefix for manual assets
        self.fund_mapping = {
            "810001": "GF_KOURACASH",  # Cash Fund
            "810002": "GF_KOURAFI",  # Fixed Interest Fund
            "810003": "GF_KOURANZEQ",  # NZ Equities Fund
            "810004": "GF_KOURAUSEQ",  # US Equities Fund
            "810005": "GF_KOURAROWEQ",  # Rest of World Equities Fund
            "810006": "GF_KOURAEMEQ",  # Emerging Markets Equities Fund
            "810007": "GF_KOURABTC",  # Bitcoin Fund
            "810008": "GF_KOURACLEAN",  # Clean Energy Fund
            "810009": "GF_KOURAPROP",  # Property Fund
            "810010": "GF_KOURASTRAT",  # Strategic Growth Fund
        }

        # Load custom fund mapping from yaml file
        if os.path.exists(mapping_file):
            try:
                with open(mapping_file, 'r') as file:
                    config = yaml.safe_load(file)
                    custom_mapping = config.get('symbol_mapping', {})
                    if custom_mapping:
                        self.fund_mapping.update(custom_mapping)
                        logger.info("Loaded custom symbol mappings from %s", mapping_file)
            except Exception as e:
                logger.warning("Failed to load mapping file %s: %s", mapping_file, e)

    def authenticate_koura(self):
        """Authenticate with Koura Wealth and get JWT token"""
        logger.info("Authenticating with Koura Wealth")

        url = "https://portal.kourawealth.co.nz/api/clients/auth/signin"
        payload = json.dumps({
            "Username": self.koura_username,
            "Password": self.koura_password
        })
        headers = {
            'Content-Type': 'application/json',
            'Origin': 'https://my.kourawealth.co.nz',
            'X-User-Tag': self.koura_user_tag
        }

        try:
            response = requests.request("POST", url, headers=headers, data=payload)
            if response.status_code == 200:
                data = response.json()
                self.koura_token = data['token']
                logger.info("Successfully authenticated with Koura Wealth")
                return True
            else:
                logger.error("Failed to authenticate with Koura: %s", response.text)
                return False
        except Exception as e:
            logger.error("Error authenticating with Koura: %s", e)
            return False

    def get_koura_accounts(self) -> List[dict]:
        """Get list of Koura accounts"""
        if not self.koura_token:
            self.authenticate_koura()

        url = "https://portal.kourawealth.co.nz/api/clients/accounts"
        headers = {
            'Authorization': f'Bearer {self.koura_token}',
            'Origin': 'https://my.kourawealth.co.nz',
            'X-User-Tag': self.koura_user_tag
        }

        try:
            response = requests.request("GET", url, headers=headers)
            if response.status_code == 200:
                return response.json()
            else:
                logger.error("Failed to get accounts: %s", response.text)
                return []
        except Exception as e:
            logger.error("Error getting accounts: %s", e)
            return []

    def get_koura_account_details(self, account_id: int) -> Optional[dict]:
        """Get detailed account information including allocations"""
        if not self.koura_token:
            self.authenticate_koura()

        url = f"https://portal.kourawealth.co.nz/api/clients/account/{account_id}"
        headers = {
            'Authorization': f'Bearer {self.koura_token}',
            'Origin': 'https://my.kourawealth.co.nz',
            'X-User-Tag': self.koura_user_tag
        }

        try:
            response = requests.request("GET", url, headers=headers)
            if response.status_code == 200:
                return response.json()
            else:
                logger.error("Failed to get account details: %s", response.text)
                return None
        except Exception as e:
            logger.error("Error getting account details: %s", e)
            return None

    def get_koura_portfolio_funds(self, account_id: int) -> List[dict]:
        """Get portfolio holdings and historical unit prices"""
        if not self.koura_token:
            self.authenticate_koura()

        url = f"https://portal.kourawealth.co.nz/api/clients/account/{account_id}/portfolio/funds"
        headers = {
            'Authorization': f'Bearer {self.koura_token}',
            'Origin': 'https://my.kourawealth.co.nz',
            'X-User-Tag': self.koura_user_tag
        }

        try:
            response = requests.request("GET", url, headers=headers)
            if response.status_code == 200:
                return response.json()
            else:
                logger.error("Failed to get portfolio funds: %s", response.text)
                return []
        except Exception as e:
            logger.error("Error getting portfolio funds: %s", e)
            return []

    def get_koura_transactions(self, account_id: int, page: int = 1, page_size: int = 100) -> dict:
        """Get account transactions (contributions, fees, etc)"""
        if not self.koura_token:
            self.authenticate_koura()

        url = f"https://portal.kourawealth.co.nz/api/clients/account/{account_id}/transactions"
        headers = {
            'Authorization': f'Bearer {self.koura_token}',
            'Origin': 'https://my.kourawealth.co.nz',
            'X-User-Tag': self.koura_user_tag
        }

        try:
            response = requests.request("GET", url, headers=headers, params={"page": page, "pageSize": page_size})
            if response.status_code == 200:
                return response.json()
            else:
                logger.error("Failed to get transactions: %s", response.text)
                return {"transactions": [], "totalCount": 0}
        except Exception as e:
            logger.error("Error getting transactions: %s", e)
            return {"transactions": [], "totalCount": 0}

    def get_all_koura_transactions(self, account_id: int) -> List[dict]:
        """Get all transactions by paginating through results"""
        all_transactions = []
        page = 1
        page_size = 100

        while True:
            result = self.get_koura_transactions(account_id, page, page_size)
            transactions = result.get("transactions", [])
            all_transactions.extend(transactions)

            if len(all_transactions) >= result.get("totalCount", 0):
                break
            page += 1

        return all_transactions

    def get_unit_price_for_date(self, fund_data: dict, transaction_date: str) -> Optional[float]:
        """Get the unit price for a fund on a specific date"""
        valuation = fund_data.get("valuation", {})

        # Try exact match first
        if transaction_date in valuation:
            return valuation[transaction_date]

        # Find closest previous date
        transaction_dt = datetime.strptime(transaction_date, "%Y-%m-%d")
        closest_date = None
        closest_price = None

        for date_str, price in valuation.items():
            date_dt = datetime.strptime(date_str, "%Y-%m-%d")
            if date_dt <= transaction_dt:
                if closest_date is None or date_dt > closest_date:
                    closest_date = date_dt
                    closest_price = price

        return closest_price

    def reconstruct_fund_purchases(self, transactions: List[dict], account_details: dict,
                                   portfolio_funds: List[dict]) -> List[dict]:
        """
        Create BUY activities for current fund holdings to show allocation breakdown.
        Uses fixed $1.00 unit price so values don't fluctuate with market prices.
        """
        activities = []

        # Create one BUY activity per fund showing current holdings
        # Use today's date so they appear as current positions
        today = datetime.now().isoformat()

        for fund in portfolio_funds:
            fund_code = str(fund.get('fundId') or fund.get('code', ''))
            fund_name = fund.get('name', 'Unknown')
            units = fund.get('units', 0)
            value = fund.get('value', 0)

            if value <= 0 or units <= 0:
                logger.info("Skipping fund %s with zero value/units", fund_name)
                continue

            # Get Ghostfolio symbol
            symbol = self.fund_mapping.get(fund_code)
            if not symbol:
                logger.warning("No symbol mapping for fund code %s", fund_code)
                continue

            # Create BUY activity with fixed $1.00 unit price
            # Quantity = dollar value, so total value stays constant
            activity = {
                "accountId": None,  # Will be set later
                "comment": f"Current holdings: {units:.4f} units @ ${value/units:.4f} per unit",
                "currency": self.ghost_currency,
                "dataSource": "MANUAL",
                "date": today,
                "fee": 0,
                "quantity": round(value, 2),  # Use dollar value as quantity
                "symbol": symbol,
                "type": "BUY",
                "unitPrice": 1.0  # Fixed price so value = quantity
            }

            activities.append(activity)
            logger.info("Created holding for %s: $%.2f NZD", fund_name, value)

        return activities

    def sync_koura(self):
        """Main sync method"""
        logger.info("Starting Koura Wealth sync")

        # Authenticate with Koura
        if not self.authenticate_koura():
            logger.error("Failed to authenticate with Koura")
            return

        # Get or create Ghostfolio account
        account_id = self.create_or_get_koura_accountId()
        if account_id == "":
            logger.info("Failed to retrieve account ID closing now")
            return

        # Get Koura account details
        account_details = self.get_koura_account_details(int(self.koura_account_id))
        if not account_details:
            logger.error("Failed to get account details")
            return

        # Get portfolio funds (for historical prices)
        portfolio_funds = self.get_koura_portfolio_funds(int(self.koura_account_id))
        if not portfolio_funds:
            logger.error("Failed to get portfolio funds")
            return

        # Get all transactions
        transactions = self.get_all_koura_transactions(int(self.koura_account_id))
        logger.info("Retrieved %d transactions from Koura", len(transactions))

        # Reconstruct fund purchases
        activities = self.reconstruct_fund_purchases(transactions, account_details, portfolio_funds)
        logger.info("Reconstructed %d fund purchase activities", len(activities))

        # Set account ID for all activities
        for activity in activities:
            activity["accountId"] = account_id

        # Get existing activities from Ghostfolio
        existing_acts = self.get_all_acts_for_account()

        # Find new activities
        diff = get_diff(existing_acts, activities)

        if len(diff) == 0:
            logger.info("Nothing new to sync")
        else:
            logger.info("Found %d new activities to sync", len(diff))
            self.import_act(diff)

        # Set cash balance to 0 since all holdings are tracked as BUY activities
        logger.info("Setting cash balance to 0 (all holdings tracked as fund activities)")
        self.set_cash_to_account(account_id, {self.ghost_currency: 0})

    # Ghostfolio API methods (same as SyncIBKR)

    def create_ghost_token(self, ghost_host, ghost_key):
        logger.info("No bearer token provided, fetching one")
        token = {
            'accessToken': ghost_key
        }

        url = f"{ghost_host}/api/v1/auth/anonymous"

        payload = json.dumps(token)
        headers = {
            'Content-Type': 'application/json'
        }
        try:
            response = requests.request("POST", url, headers=headers, data=payload)
        except Exception as e:
            logger.info(e)
            return ""
        if response.status_code == 201:
            logger.info("Bearer token fetched")
            return response.json()["authToken"]
        logger.info("Failed fetching bearer token")
        return ""

    def set_cash_to_account(self, account_id, cash: dict):
        if cash is None or len(cash) == 0:
            logger.info("No cash set, no cash retrieved")
            return False
        for currency, amount in cash.items():
            amount_data = {
                "balance": amount,
                "id": account_id,
                "currency": currency,
                "isExcluded": False,
                "name": self.ghost_account_name,
                "platformId": self.koura_platform
            }
            logger.info("Updating Cash for account " + account_id + ": " + json.dumps(amount_data))

            url = f"{self.ghost_host}/api/v1/account/{account_id}"

            payload = json.dumps(amount_data)
            headers = {
                'Authorization': f"Bearer {self.ghost_token}",
                'Content-Type': 'application/json'
            }
            try:
                response = requests.request("PUT", url, headers=headers, data=payload)
            except Exception as e:
                logger.info(e)
                return
            if response.status_code == 200:
                logger.info(f"Updated Cash for account {response.json()['id']}")
            else:
                logger.info("Failed create: " + response.text)

    def import_act(self, bulk):
        chunks = generate_chunks(sorted(bulk, key=lambda x: x["date"]), 10)
        for acts in chunks:
            logger.info("Adding activities:\n%s", json.dumps(acts, indent=4))

            url = f"{self.ghost_host}/api/v1/import"
            payload = json.dumps({"activities": acts})
            headers = {
                'Authorization': f"Bearer {self.ghost_token}",
                'Content-Type': 'application/json'
            }

            try:
                response = requests.request("POST", url, headers=headers, data=payload)
            except Exception as e:
                logger.info(e)
                return False
            if response.status_code == 201:
                logger.info("Added activities. Response:\n%s", json.dumps(response.json(), indent=4))
            else:
                logger.info("Failed to create: " + response.text)
            if response.status_code != 201:
                return False
        return True

    def create_koura_account(self):
        logger.info("Creating Koura account in Ghostfolio")
        account = {
            "balance": 0,
            "currency": self.ghost_currency,
            "isExcluded": False,
            "name": self.ghost_account_name,
            "platformId": self.koura_platform
        }

        url = f"{self.ghost_host}/api/v1/account"

        payload = json.dumps(account)
        headers = {
            'Authorization': f"Bearer {self.ghost_token}",
            'Content-Type': 'application/json'
        }
        try:
            response = requests.request("POST", url, headers=headers, data=payload)
        except Exception as e:
            logger.info(e)
            return ""
        if response.status_code == 201:
            logger.info("Koura account: " + response.json()["id"])
            return response.json()["id"]
        logger.info("Failed creating ")
        return ""

    def get_all_accounts(self):
        logger.info("Finding all accounts")
        url = f"{self.ghost_host}/api/v1/account"

        payload = {}
        headers = {
            'Authorization': f"Bearer {self.ghost_token}",
        }
        try:
            response = requests.request("GET", url, headers=headers, data=payload)
        except Exception as e:
            logger.info(e)
            return []
        if response.status_code == 200:
            return response.json()['accounts']
        else:
            raise Exception(response)

    def create_or_get_koura_accountId(self):
        if self.account_id is not None:
            return self.account_id

        accounts = self.get_all_accounts()
        logger.info("Accounts: %s", json.dumps(accounts, indent=4))
        for account in accounts:
            if account["name"] == self.ghost_account_name:
                logger.info("Koura account: %s", account["id"])
                self.account_id = account["id"]
                return account["id"]

        self.account_id = self.create_koura_account()
        return self.account_id

    def delete_all_acts(self):
        acts = self.get_all_acts_for_account()

        if not acts:
            logger.info("No activities to delete")
            return True

        url = f"{self.ghost_host}/api/v1/order"

        payload = {}
        headers = {
            'Authorization': f"Bearer {self.ghost_token}",
        }
        try:
            response = requests.request("DELETE",
                                        url,
                                        headers=headers,
                                        params={"accounts": self.create_or_get_koura_accountId()},
                                        data=payload)
        except Exception as e:
            logger.info(e)
            return False

        return response.status_code == 200

    def get_all_acts_for_account(self, account_id: str = None, range: str = None, symbol: str = None):
        if account_id is None:
            account_id = self.create_or_get_koura_accountId()

        url = f"{self.ghost_host}/api/v1/order"

        payload = {}
        headers = {
            'Authorization': f"Bearer {self.ghost_token}",
        }
        try:
            response = requests.request("GET",
                                        url,
                                        headers=headers,
                                        params={"accounts": account_id,
                                                "range": range,
                                                "symbol": symbol},
                                        data=payload)
        except Exception as e:
            logger.info(e)
            return []

        if response.status_code == 200:
            return response.json()['activities']
        else:
            return []
