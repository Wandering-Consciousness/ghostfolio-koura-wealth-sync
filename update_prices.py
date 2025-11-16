#!/usr/bin/env python3
import os
from SyncKoura import SyncKoura
import requests
import json

ghost_host = os.environ.get("GHOST_HOST")
ghost_token = os.environ.get("GHOST_TOKEN")
koura_username = os.environ.get("KOURA_USERNAME")
koura_password = os.environ.get("KOURA_PASSWORD")
koura_account_id = os.environ.get("KOURA_ACCOUNT_ID")

# Create sync instance and authenticate
# Pass empty string for ghost_key since we're using ghost_token directly
sync = SyncKoura(ghost_host, koura_username, koura_password, "", ghost_token, koura_account_id, "Koura Wealth", "NZD", "")

# Get portfolio funds with current prices
portfolio_funds = sync.get_koura_portfolio_funds(int(koura_account_id))

print("Current Unit Prices from Koura:")
print("="*80)

fund_mapping = {
    "810002": "GF_KOURAFI",
    "810003": "GF_KOURANZEQ",
    "810004": "GF_KOURAUSEQ",
    "810005": "GF_KOURAROWEQ",
    "810006": "GF_KOURAEMEQ",
    "810007": "GF_KOURABTC",
    "810008": "GF_KOURACLEAN",
    "810009": "GF_KOURAPROP",
    "810010": "GF_KOURASTRAT",
}

for fund in portfolio_funds:
    fund_id = str(fund.get('fundId'))
    name = fund.get('name', 'Unknown')
    symbol = fund_mapping.get(fund_id, f"UNKNOWN_{fund_id}")

    # Get latest price from valuation
    valuation = fund.get('valuation', {})
    if valuation:
        latest_date = max(valuation.keys())
        latest_price = valuation[latest_date]

        print(f"{symbol}: {name}")
        print(f"  Latest price ({latest_date}): ${latest_price}")

        # Update the price in Ghostfolio
        market_data_payload = {
            "marketData": {
                latest_date: latest_price
            }
        }

        url = f"{ghost_host}/api/v1/admin/profile-data/MANUAL/{symbol}"
        headers = {
            "Authorization": f"Bearer {ghost_token}",
            "Content-Type": "application/json"
        }

        response = requests.patch(url, headers=headers, json=market_data_payload)

        if response.status_code in [200, 201]:
            print(f"  ✓ Updated price in Ghostfolio")
        else:
            print(f"  ✗ Failed to update: {response.status_code} - {response.text}")
        print()
