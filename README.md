# Ghostfolio-Koura-Wealth-Sync

Sync your Ghostfolio portfolio with Koura Wealth KiwiSaver accounts.

## Features

- Automatically syncs Koura Wealth KiwiSaver contributions to Ghostfolio
- Tracks contribution history (employee, employer, voluntary)
- Maintains accurate account balance matching Koura app
- Supports multiple accounts
- Can be run manually or on a cron schedule
- Docker support for easy deployment

## How It Works

Since Koura Wealth is a managed fund platform (not a stock broker), this sync tool:

1. Fetches all contribution transactions from Koura Wealth API
2. Creates INTEREST activities in Ghostfolio to track contribution history
3. Sets the account cash balance to match your current Koura balance
4. Maintains accurate total value without trying to track individual fund prices

**Note:** This tool tracks contributions as cash flow rather than individual fund purchases. This approach ensures the Ghostfolio account balance always matches your actual Koura Wealth balance, since Ghostfolio cannot automatically track market prices for managed KiwiSaver funds.

## Setup

### Prerequisites

- A Koura Wealth account
- A Ghostfolio account (cloud or self-hosted)
- Python 3.11+ (if running locally) or Docker

### Koura Wealth

1. Log into your Koura Wealth account at https://my.kourawealth.co.nz/
2. Note your account number (e.g., KOU003925)
3. Find your account ID:
   - Open browser developer tools (F12)
   - Go to the Network tab
   - Refresh the page
   - Look for a request to `/api/clients/accounts`
   - Find the `id` field in the response (e.g., 4248)

### Ghostfolio

**Option 1: Using User Key (Cloud/Self-Hosted)**
1. Get your Ghostfolio user **KEY** from account settings
2. Set `GHOST_KEY` in your `.env` file

**Option 2: Using Auth Token (Self-Hosted)**
1. Generate an authentication token:

```bash
curl -X POST -H "Content-Type: application/json" \
  -d '{ "accessToken": "YOUR-USER-KEY-GOES-HERE" }' \
  https://ghostfol.io/api/v1/auth/anonymous
```

2. Save the `authToken` from the response
3. Set `GHOST_TOKEN` in your `.env` file

**Option 3: Creating Manual Assets (Required)**

Before running the sync, you need to create 9 manual asset profiles in Ghostfolio for the Koura funds:

1. In Ghostfolio, go to Admin → Asset Profiles
2. Click "Add Manually" for each fund
3. Create the following assets:

| Symbol | Name | Currency | Asset Class |
|--------|------|----------|-------------|
| GF_KOURAFI | Koura Fixed Interest Fund | NZD | Fixed Income |
| GF_KOURANZEQ | Koura NZ Equities Fund | NZD | Equity |
| GF_KOURAUSEQ | Koura US Equities Fund | NZD | Equity |
| GF_KOURAROWEQ | Koura Rest of World Equities Fund | NZD | Equity |
| GF_KOURAEMEQ | Koura Emerging Markets Equities Fund | NZD | Equity |
| GF_KOURABTC | Koura Bitcoin Fund | NZD | Alternative Investment |
| GF_KOURACLEAN | Koura Clean Energy Fund | NZD | Equity |
| GF_KOURAPROP | Koura Property Fund | NZD | Real Estate |
| GF_KOURASTRAT | Koura Strategic Growth Fund | NZD | Equity |

Set **Data Source** to **MANUAL** for all assets.

### Configuration

1. Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```

2. Edit `.env` with your credentials:
```bash
KOURA_USERNAME=your-email@example.com
KOURA_PASSWORD=your-password
KOURA_ACCOUNT_ID=4248

GHOST_HOST=https://ghostfol.io
GHOST_KEY=your-ghostfolio-user-key

GHOST_ACCOUNT_NAME=Koura Wealth
GHOST_CURRENCY=NZD
```

### Platform ID (Self-Hosted Only)

If you're using a self-hosted Ghostfolio instance, you need to create a platform and get its ID:

1. In Ghostfolio, go to Settings → Platforms
2. Create a new platform called "Koura Wealth"
3. Get the platform ID:

```bash
curl "http://your-ghostfolio-host:3333/api/v1/account" \
     -H "Authorization: Bearer $GHOST_TOKEN"
```

4. Add it to your `.env`:
```bash
GHOST_KOURA_PLATFORM=your-platform-id
```

## Running

### Local

```bash
# Install dependencies
pip install -r requirements.txt

# Run sync
python main.py
```

### Docker

```bash
# Build image
docker build -t ghostfolio-koura-sync .

# Run once
docker run --env-file .env ghostfolio-koura-sync

# Run with cron schedule (every 6 hours)
docker run --env-file .env -e CRON="0 */6 * * *" ghostfolio-koura-sync
```

### Docker Compose

Create a `docker-compose.yml`:

```yaml
version: '3.8'

services:
  koura-sync:
    build: .
    env_file: .env
    environment:
      - CRON=0 */6 * * *
    restart: unless-stopped
```

Run with:
```bash
docker-compose up -d
```

## Operations

The `OPERATION` environment variable controls what the sync tool does:

- `SYNCKOURA` (default): Sync transactions from Koura to Ghostfolio
- `GET_ALL_ACTS`: Display all activities in the Ghostfolio account
- `DELETE_ALL_ACTS`: Delete all activities from the Ghostfolio account

## Fund Symbols

The sync tool uses the following Ghostfolio symbols for Koura funds (must be created manually as described in setup):

| Fund | Symbol | Asset Class |
|------|--------|-------------|
| Cash Fund | GF_KOURACASH | Liquidity |
| Fixed Interest Fund | GF_KOURAFI | Fixed Income |
| NZ Equities Fund | GF_KOURANZEQ | Equity |
| US Equities Fund | GF_KOURAUSEQ | Equity |
| Rest of World Equities Fund | GF_KOURAROWEQ | Equity |
| Emerging Markets Equities Fund | GF_KOURAEMEQ | Equity |
| Bitcoin Fund | GF_KOURABTC | Alternative Investment |
| Clean Energy Fund | GF_KOURACLEAN | Equity |
| Property Fund | GF_KOURAPROP | Real Estate |
| Strategic Growth Fund | GF_KOURASTRAT | Equity |

## Symbol Mapping

You can customize fund symbol mappings in `mapping.yaml`:

```yaml
symbol_mapping:
  "810003": "CUSTOM-NZ-EQUITIES"
  "810004": "CUSTOM-US-EQUITIES"
```

## Multiple Accounts

You can sync multiple Koura accounts by providing comma-separated values:

```bash
KOURA_USERNAME=user1@example.com,user2@example.com
KOURA_PASSWORD=pass1,pass2
KOURA_ACCOUNT_ID=4248,4249
OPERATION=SYNCKOURA,SYNCKOURA
```

## Troubleshooting

### No activities are synced

- Check that your Koura credentials are correct
- Verify your account ID is correct
- Ensure you have contribution transactions in your Koura account

### Authentication errors

- Make sure your Ghostfolio token is valid (they expire after some time)
- Regenerate the token if needed

### Missing funds

- Check that your chosen allocation includes the funds
- Verify the fund codes in the API response match the mapping

## Contributing

Feel free to submit issues or pull requests!

## License

MIT

## Acknowledgments

Based on the [ghostfolio-sync](https://github.com/agusalex/ghostfolio-sync) project by @agusalex.
