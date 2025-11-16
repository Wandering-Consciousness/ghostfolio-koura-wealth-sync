#!/usr/bin/env python3
import requests
import json
import os

GHOST_HOST = os.environ.get("GHOST_HOST", "https://ghostfol.io")
GHOST_TOKEN = os.environ.get("GHOST_TOKEN")

# Define all 9 Koura funds
funds = [
    {"symbol": "GF_KOURAFI", "name": "Koura Fixed Interest Fund", "assetClass": "EQUITY", "assetSubClass": "MUTUALFUND"},
    {"symbol": "GF_KOURANZEQ", "name": "Koura NZ Equities Fund", "assetClass": "EQUITY", "assetSubClass": "MUTUALFUND"},
    {"symbol": "GF_KOURAUSEQ", "name": "Koura US Equities Fund", "assetClass": "EQUITY", "assetSubClass": "MUTUALFUND"},
    {"symbol": "GF_KOURAROWEQ", "name": "Koura Rest of World Equities Fund", "assetClass": "EQUITY", "assetSubClass": "MUTUALFUND"},
    {"symbol": "GF_KOURAEMEQ", "name": "Koura Emerging Markets Equities Fund", "assetClass": "EQUITY", "assetSubClass": "MUTUALFUND"},
    {"symbol": "GF_KOURABTC", "name": "Koura Bitcoin Fund", "assetClass": "EQUITY", "assetSubClass": "MUTUALFUND"},
    {"symbol": "GF_KOURACLEAN", "name": "Koura Clean Energy Fund", "assetClass": "EQUITY", "assetSubClass": "MUTUALFUND"},
    {"symbol": "GF_KOURAPROP", "name": "Koura Property Fund", "assetClass": "EQUITY", "assetSubClass": "MUTUALFUND"},
    {"symbol": "GF_KOURASTRAT", "name": "Koura Strategic Growth Fund", "assetClass": "EQUITY", "assetSubClass": "MUTUALFUND"},
]

headers = {
    "Authorization": f"Bearer {GHOST_TOKEN}",
    "Content-Type": "application/json"
}

created_mapping = {}

for fund in funds:
    # Step 1: Create the profile using POST /api/v1/admin/profile-data/{dataSource}/{symbol}
    url = f"{GHOST_HOST}/api/v1/admin/profile-data/MANUAL/{fund['symbol']}"

    print(f"Creating asset: {fund['name']} ({fund['symbol']})")
    response = requests.post(url, headers=headers)

    if response.status_code in [200, 201]:
        result = response.json()
        print(f"  ✓ Created profile successfully")

        # Step 2: Update the profile with detailed information using PATCH
        patch_url = f"{GHOST_HOST}/api/v1/admin/profile-data/MANUAL/{fund['symbol']}"
        patch_payload = {
            "assetClass": fund["assetClass"],
            "assetSubClass": fund["assetSubClass"],
            "currency": "NZD",
            "name": fund["name"]
        }

        patch_response = requests.patch(patch_url, headers=headers, json=patch_payload)

        if patch_response.status_code in [200, 201]:
            updated_result = patch_response.json()
            print(f"  ✓ Updated profile details successfully")
            print(f"    Symbol: {updated_result.get('symbol')}")
            created_mapping[fund["symbol"]] = updated_result.get("symbol")
        else:
            print(f"  ⚠ Profile created but update failed: {patch_response.status_code}")
            print(f"    {patch_response.text}")
            created_mapping[fund["symbol"]] = result.get("symbol")
    else:
        print(f"  ✗ Failed: {response.status_code}")
        print(f"    {response.text}")

print("\n" + "="*60)
print("Fund Mapping for SyncKoura.py:")
print("="*60)
for koura_id, symbol in [("810002", "GF_KOURAFI"), ("810003", "GF_KOURANZEQ"),
                         ("810004", "GF_KOURAUSEQ"), ("810005", "GF_KOURAROWEQ"),
                         ("810006", "GF_KOURAEMEQ"), ("810007", "GF_KOURABTC"),
                         ("810008", "GF_KOURACLEAN"), ("810009", "GF_KOURAPROP"),
                         ("810010", "GF_KOURASTRAT")]:
    if symbol in created_mapping:
        print(f'    "{koura_id}": "{created_mapping[symbol]}",  # {symbol}')
