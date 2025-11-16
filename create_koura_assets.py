"""
Helper script to create Koura fund assets in Ghostfolio.
Run this ONCE before the first sync to register the custom fund symbols.
"""

import json
import os
import requests
import logging

template = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
logging.basicConfig(level=logging.INFO, format=template)
logger = logging.getLogger(__name__)

# Load environment variables
ghost_host = os.environ.get("GHOST_HOST", "https://ghostfol.io")
ghost_token = os.environ.get("GHOST_TOKEN", "")

if not ghost_token:
    logger.error("GHOST_TOKEN environment variable not set")
    exit(1)

# Koura funds to create
KOURA_FUNDS = [
    {"symbol": "KOURANZEQ", "name": "Koura NZ Equities Fund", "code": "810003"},
    {"symbol": "KOURAUSEQ", "name": "Koura US Equities Fund", "code": "810004"},
    {"symbol": "KOURAROWEQ", "name": "Koura Rest of World Equities Fund", "code": "810005"},
    {"symbol": "KOURAEMEQ", "name": "Koura Emerging Markets Equities Fund", "code": "810006"},
    {"symbol": "KOURABTC", "name": "Koura Bitcoin Fund", "code": "810007"},
    {"symbol": "KOURACLEAN", "name": "Koura Clean Energy Fund", "code": "810008"},
    {"symbol": "KOURAPROP", "name": "Koura Property Fund", "code": "810009"},
]

def create_symbol_via_transaction(symbol_data):
    """
    Create a symbol by importing a dummy transaction.
    This is a workaround since Ghostfolio creates symbols when importing activities.
    """
    logger.info(f"Creating symbol: {symbol_data['symbol']} - {symbol_data['name']}")

    # We'll use the import endpoint with dataSource: MANUAL
    # This might require the symbol to exist or create it
    url = f"{ghost_host}/api/v1/admin/market-data"

    payload = {
        "symbol": symbol_data['symbol'],
        "dataSource": "MANUAL",
        "currency": "NZD",
        "name": symbol_data['name'],
    }

    headers = {
        'Authorization': f"Bearer {ghost_token}",
        'Content-Type': 'application/json'
    }

    try:
        response = requests.post(url, headers=headers, json=payload)
        if response.status_code in [200, 201]:
            logger.info(f"✓ Created {symbol_data['symbol']}")
            return True
        else:
            logger.warning(f"✗ Failed to create {symbol_data['symbol']}: {response.text}")
            return False
    except Exception as e:
        logger.error(f"Error creating {symbol_data['symbol']}: {e}")
        return False

if __name__ == "__main__":
    logger.info("Creating Koura fund assets in Ghostfolio...")
    logger.info(f"Ghost host: {ghost_host}")

    success_count = 0
    for fund in KOURA_FUNDS:
        if create_symbol_via_transaction(fund):
            success_count += 1

    logger.info(f"Created {success_count}/{len(KOURA_FUNDS)} fund symbols")

    if success_count < len(KOURA_FUNDS):
        logger.warning("Some symbols could not be created automatically.")
        logger.warning("You may need to create them manually in Ghostfolio:")
        logger.warning("1. Go to your Ghostfolio admin panel")
        logger.warning("2. Navigate to Market Data / Assets")
        logger.warning("3. Create custom assets with the symbols listed above")
