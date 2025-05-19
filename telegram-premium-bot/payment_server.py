# payment_server.py – Flask endpoint for Helius webhook

import os, json
from datetime import datetime, timedelta

from flask import Flask, request
from telegram import Bot

BOT_TOKEN   = os.getenv("BOT_TOKEN")
USDC_MINT   = "EPjFWdd5AufqSSqeM2q4JmQ4Xi1xF1n7THDq73o1gmGk"
PRICE_USDC  = 20
bot = Bot(BOT_TOKEN)
app = Flask(__name__)

def load_members():
    with open("members.json") as f:
        return json.load(f)

def save_members(m):
    with open("members.json", "w") as f:
        json.dump(m, f, indent=2)

# build quick lookup {deposit_address: user_id}
def build_addr_map(members):
    return {v["deposit_address"]: int(uid) for uid, v in members.items()}

@app.route("/helius", methods=["POST"])
def helius():
    data = request.get_json()
    members = load_members()
    addr_map = build_addr_map(members)

    for ev in data.get("events", []):
        if ev["type"] != "TOKEN_TRANSFER":
            continue
        tk = ev["tokenTransfer"]
        if tk["mint"] != USDC_MINT or tk["tokenAmount"] < PRICE_USDC:
            continue

        dest  = tk["toUserAccount"]
        uid   = addr_map.get(dest)
        if not uid:
            continue          # address not linked to any user

        # activate membership 30 days
        members[str(uid)]["expires"] = (datetime.utcnow() + timedelta(days=30)).isoformat()
        save_members(members)
        bot.send_message(uid, "✅ Payment received – membership activated for 30 days!")
    return "", 200

# --- expose via ngrok for local testing ---
if __name__ == "__main__":
    from pyngrok import ngrok
    public = ngrok.connect(5000).public_url
    print("Expose URL:", public + "/helius")
    app.run(port=5000)
