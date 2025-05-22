import os
import requests
from datetime import datetime, timedelta

MEMBERSHIP_TIERS = {
    "10_days": {"price_usd": 39.6, "days": 10},
    "1_month": {"price_usd": 69.3, "days": 30},
    "lifetime": {"price_usd": 96.3, "days": None},  # None means no expiry
}

HELIUS_API_KEY = os.getenv("0d325a71-6df7-4cc9-b02f-91ca88637920")
WEBHOOK_ID = os.getenv("1d5baa2d-5643-4871-995d-52083b707723")  # store your webhook id in env for security

def helius_add_address(pubkey: str) -> bool:
    """
    Add a new Solana address to the Helius webhook's monitored accounts.

    Returns True if successful, False otherwise.
    """
    url = f"https://api.helius.xyz/v0/webhooks/{WEBHOOK_ID}/addMonitoredAccounts?api-key={HELIUS_API_KEY}"
    payload = {
        "accounts": [pubkey]
    }
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        return True
    except Exception as e:
        print(f"Error adding address to Helius webhook: {e}")
        return False

def get_expiration_date(tier_key: str) -> datetime | None:
    """
    Return expiration datetime for given membership tier or None if lifetime.
    """
    tier = MEMBERSHIP_TIERS.get(tier_key)
    if not tier:
        return None
    if tier["days"] is None:
        return None
    return datetime.utcnow() + timedelta(days=tier["days"])
