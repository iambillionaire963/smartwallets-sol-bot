import os
import json
import logging
from datetime import datetime, timedelta

from telegram import Update, constants
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from solders.keypair import Keypair
from dotenv import load_dotenv

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
PRICE_USDC = 20  # membership price
KEY_DIR = "keys"  # where keypairs live
os.makedirs(KEY_DIR, exist_ok=True)

# ---------- helpers ----------

def load_members():
    if not os.path.exists("members.json"):
        return {}
    with open("members.json") as f:
        return json.load(f)

def save_members(members):
    with open("members.json", "w") as f:
        json.dump(members, f, indent=2)

def new_deposit_address(user_id: str) -> str:
    """
    Generate a new Solana keypair (pure Python) and return its public address.
    """
    kp = Keypair.generate()
    pubkey = str(kp.public_key)
    # save secret key for audits/refunds
    with open(f"{KEY_DIR}/{user_id}.json", "w") as f:
        json.dump(list(kp.secret_key), f)
    return pubkey

# ---------- command handlers ----------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = (
        "🚨*Quantum AI Memecoin Alerts by Solana100xCall* 🚨\n\n"
        "📡 Real-time entries from Solana’s smartest wallets — delivered by our AI bot.\n\n"
        "Our custom bot monitors 300+ high-PNL wallets — whales, insiders, and snipers making $100k+ weekly. "
        "It tracks their purchases, filters them with AI, and sends you the hottest entries as they happen. "
        "Not scanning. No second-guessing. Just winning setups.\n\n"
        "✅ 30+ filtered alerts every day\n"
        "✅ Copy-paste contracts for lightning-fast entries\n"
        "✅ AI-powered — not crowdsourced or delayed\n"
        "✅ Only top wallets make the list\n\n"
        "🔓 Choose your membership below and plug into real-time smart money flow.\n\n"
        "💬 Questions? DM @The100xMooncaller\n"
        "📈 Track record: t.me/solana100xcall/4046"
    )
    await update.message.reply_text(message, parse_mode=constants.ParseMode.MARKDOWN)

async def buy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    uid = str(user.id)
    members = load_members()

    # reuse address if it exists, else create
    addr = members.get(uid, {}).get("deposit_address")
    if not addr:
        addr = new_deposit_address(uid)
        # TODO: call helius_add_address(addr) → add to webhook list
        members[uid] = {"username": user.username, "deposit_address": addr}
        save_members(members)

    msg = (
        f"💳 Send *{PRICE_USDC} USDC* (SPL) to **your personal address**:\n"
        f"`{addr}`\n\n"
        "We’ll confirm automatically within a minute after payment."
    )
    await update.message.reply_text(msg, parse_mode=constants.ParseMode.MARKDOWN)

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    members = load_members()
    data = members.get(uid, {})
    exp = data.get("expires")
    if exp and datetime.fromisoformat(exp) > datetime.utcnow():
        delta = datetime.fromisoformat(exp) - datetime.utcnow()
        await update.message.reply_text(f"✅ Active • {delta.days}d {delta.seconds // 3600}h left.")
    else:
        await update.message.reply_text("❌ No active membership. Use /buy to get started.")

# ---------- main ----------

def main():
    logging.basicConfig(level=logging.INFO)
    app = ApplicationBuilder().token(BOT_TOKEN).get_updates_request({'proxy': None}).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("buy", buy))
    app.add_handler(CommandHandler("status", status))

    print("Bot started...")
    app.run_polling()

if __name__ == "__main__":
    main()