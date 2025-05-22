# payment_server.py – Flask endpoint for Helius webhook

import os
import json
import requests
from datetime import datetime, timedelta

from flask import Flask, request
from telegram import Bot
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
USDC_MINT = "EPjFWdd5AufqSSqeM2q4JmQ4Xi1xF1n7THDq73o1gmGk"

# Membership pricing in USD:
PRICE_10D = 39.6
PRICE_1M = 69.3
PRICE_LIFE = 96.3

bot = Bot(BOT_TOKEN)
app = Flask(__name__)

def load_members():
    if not os.path.exists("members.json"):
        return {}
    with open("members.json") as f:
        return json.load(f)

def save_members(m):
    with open("members.json", "w") as f:
        json.dump(m, f, indent=2)

# build quick lookup {deposit_address: user_id}
def build_addr_map(members):
    return {v["deposit_address"]: int(uid) for uid, v in members.items()}

def get_sol_price():
    # Fetch current SOL price in USD from CoinGecko
    try:
        resp = requests.get("https://api.coingecko.com/api/v3/simple/price?ids=solana&vs_currencies=usd")
        resp.raise_for_status()
        data = resp.json()
        return data["solana"]["usd"]
    except Exception as e:
        print("Error fetching SOL price:", e)
        return None

def process_payment(uid: str, token_type: str, amount: float):
    """
    Process payment amount and token type, update membership expiration accordingly.
    Returns True if payment is sufficient and membership activated.
    """
    members = load_members()
    now = datetime.utcnow()

    if uid not in members:
        return False  # unknown user

    current_exp_str = members[uid].get("expires")
    current_exp = datetime.fromisoformat(current_exp_str) if current_exp_str else now

    # Extend from current expiration if in future, else from now
    start_time = current_exp if current_exp > now else now

    # Determine membership days to add based on amount and token type
    # Convert SOL to USD if needed
    if token_type == "SOL":
        sol_price = get_sol_price()
        if sol_price is None:
            return False  # Could not get SOL price, reject for now
        usd_amount = amount * sol_price
    elif token_type == "USDC":
        usd_amount = amount
    else:
        return False  # unsupported token

    # Check which membership tier fits
    if usd_amount >= PRICE_LIFE:
        new_exp = start_time + timedelta(days=365*100)  # effectively lifetime
    elif usd_amount >= PRICE_1M:
        new_exp = start_time + timedelta(days=30)
    elif usd_amount >= PRICE_10D:
        new_exp = start_time + timedelta(days=10)
    else:
        return False  # insufficient payment

    members[uid]["expires"] = new_exp.isoformat()
    save_members(members)
    return True


@app.route("/helius", methods=["POST"])
def helius():
    data = request.get_json()
    members = load_members()
    addr_map = build_addr_map(members)

    for ev in data.get("events", []):
        # Handle USDC token transfers
        if ev["type"] == "TOKEN_TRANSFER":
            tk = ev["tokenTransfer"]
            dest = tk["toUserAccount"]
            uid = addr_map.get(dest)
            if not uid:
                continue

            mint = tk["mint"]
            amount = float(tk["tokenAmount"])

            if mint == USDC_MINT:
                success = process_payment(str(uid), "USDC", amount)
                if success:
                    bot.send_message(uid, "✅ Payment received – membership activated/extended!")
                else:
                    bot.send_message(uid, "❌ Payment received but amount is insufficient.")
            continue

        # Handle SOL transfers
        if ev["type"] == "SOL_TRANSFER":
            sol = ev["solTransfer"]
            dest = sol["toUserAccount"]
            uid = addr_map.get(dest)
            if not uid:
                continue

            amount = float(sol["lamports"]) / 1_000_000_000  # convert lamports to SOL

            success = process_payment(str(uid), "SOL", amount)
            if success:
                bot.send_message(uid, "✅ SOL payment received – membership activated/extended!")
            else:
                bot.send_message(uid, "❌ SOL payment received but amount is insufficient.")
            continue

    return "", 200


# --- expose via ngrok for local testing ---
if __name__ == "__main__":
    from pyngrok import ngrok
    public = ngrok.connect(5000).public_url
    print("Expose URL:", public + "/helius")
    app.run(port=5000)
