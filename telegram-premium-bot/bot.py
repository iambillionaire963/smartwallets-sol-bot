# telegram-premium-bot/bot.py

import os
import logging
from flask import Flask
from threading import Thread
from telegram import Update, constants, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, CallbackQueryHandler

# ---------- Flask Keep Alive (for UptimeRobot) ----------
app = Flask('')

@app.route('/')
def home():
    return "✅ Bot is alive!", 200

def run():
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 3000)))

def keep_alive():
    Thread(target=run).start()

# ---------- Bot Setup ----------
BOT_TOKEN = os.getenv("BOT_TOKEN")
MEMBERSHIP_LINK = "https://t.me/onlysubsbot?start=bXeGHtzWUbduBASZemGJf"

# ---------- Handlers ----------

def build_membership_message() -> str:
    return (
        "🚨 Quantum AI Memecoin Alerts by Solana100xCall 🚨\n\n"
        "📡 Real-time entries from Solana's smartest wallets — delivered by our AI bot.\n\n"
        "✅ 30+ filtered alerts every day\n"
        "✅ Copy-paste contracts for lightning-fast entries\n"
        "✅ AI-powered — not crowdsourced or delayed\n"
        "✅ Only top wallets make the list\n\n"
        "🔓 Choose your membership below and plug into real-time smart money flow.\n\n"
        "💬 Questions? DM [@The100xMooncaller](https://t.me/The100xMooncaller)\n"
        "📈 Track record: t.me/solana100xcall/4046\n\n"
        "🔒 Telegram access\n"
        "Quantum AI Memecoin Alerts By Solana100xcall 🫡"
    )

ADMIN_ID = 7851863021  # 🔁 Replace with your actual Telegram ID

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    payload = context.args[0] if context.args else None

    # Log who started and with what payload (for console)
    logging.info(f"[START] User {user.id} (@{user.username}) joined with payload: {payload}")

    # ✅ Send admin notification
    first_name = user.first_name or "Unknown"
    username = f"@{user.username}" if user.username else "(no username)"
    display_name = f"{first_name}🪐 ({username})"
    user_code = f"#u{user.id}"

    admin_message = (
        f"{display_name} ({user_code}) has just launched this bot for the first time.\n\n"
        f"You can send a private message to this member by replying to this message."
    )
    await context.bot.send_message(chat_id=ADMIN_ID, text=admin_message)

    # 🔽 Your existing welcome message
    message = (
        "🚀 *Welcome to Quantum AI Memecoin Alerts* 🚀\n\n"
        "📡 _Solana’s smartest wallets tracked by our AI — in real time._\n\n"
        "Here’s what you unlock:\n"
        "✅ 30+ filtered alerts/day\n"
        "✅ Copy-paste contracts\n"
        "✅ Early low-cap plays\n"
        "✅ Real-time wallet activity from million-dollar snipers\n\n"
        "🔬 Our AI scans 300+ wallets nonstop:\n"
        "• Whales\n"
        "• Snipers\n"
        "• KOL insiders\n"
        "• Bot networks\n\n"
        "🧠 It detects:\n"
        "• Smart money inflow\n"
        "• High-liquidity new launches\n"
        "• Tokens that pump fast, not memes that flop\n\n"
        "💰 Stop chasing. Start front-running.\n\n"
        "👇 Tap below to activate access and catch the next 10x–50x:"
    )

    keyboard = [[InlineKeyboardButton("🚀 Get Premium Access", url=MEMBERSHIP_LINK)]]
    await update.message.reply_text(
        message,
        parse_mode=constants.ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(keyboard),
        disable_web_page_preview=True
    )

async def buy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = "👉 To get started, click the button below, select your membership, and proceed to payment:"
    keyboard = [[InlineKeyboardButton("🚀 Get Premium Access", url=MEMBERSHIP_LINK)]]
    await update.message.reply_text(message, reply_markup=InlineKeyboardMarkup(keyboard))

async def subscribe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = "🔥 Ready to unlock premium alerts?\n\nChoose your membership and activate full access now:"
    keyboard = [[InlineKeyboardButton("🚀 Get Premium Access", url=MEMBERSHIP_LINK)]]
    await update.message.reply_text(message, reply_markup=InlineKeyboardMarkup(keyboard))

async def join(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = (
        "📢 *Stay Ahead with Solana100xcall*\n\n"
        "Before you unlock Premium, join our *FREE public channel* to see why thousands trust our alpha.\n\n"
        "🔥 Live calls, charts, and sneak peeks into the exact kind of alerts our AI delivers to Premium members.\n\n"
        "👇 Tap below to join the official channel:"
    )
    keyboard = [[InlineKeyboardButton("📲 Join @Solana100xcall", url="https://t.me/Solana100xcall")]]
    await update.message.reply_text(message, parse_mode=constants.ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(keyboard), disable_web_page_preview=True)

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Use /buy to view membership options.")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = (
        "🧠 *How It Works*\n"
        "Our AI tracks real-time smart money on Solana — wallets making $100k+ each week.\n"
        "When it detects a high-potential play, you get an alert *instantly*.\n\n"
        "📡 *What You Get:*\n"
        "• 30+ real-time alerts/day (more when the market moves)\n"
        "• Focused on top wallets, early buys & liquidity inflow\n"
        "• Alerts include token info, market cap, and tap-to-copy contract address\n\n"
        "💸 *How to Subscribe:*\n"
        "Tap the button below to choose your membership and unlock full access.\n"
        "Payments are processed securely via Telegram — in SOL or USDC.\n\n"
        "❓ *Common Questions:*\n"
        "• Is this manual? → No. It’s 100% AI-powered.\n"
        "• Is this fast? → Yes. No delays. No crowdsourced nonsense.\n"
        "• Do alerts come at night? → Most happen during US trading hours.\n\n"
        "Need help? Message [@The100xMooncaller](https://t.me/The100xMooncaller)"
    )
    keyboard = [[InlineKeyboardButton("🚀 Get Premium Access", url=MEMBERSHIP_LINK)]]
    await update.message.reply_text(message, parse_mode=constants.ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(keyboard), disable_web_page_preview=True)

async def support(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = (
        "💬 *Need Help or Have Questions?*\n\n"
        "We're here to help you 24/7.\n\n"
        "• 👨‍💻 Tech/Access Issues → [@The100xMooncaller](https://t.me/The100xMooncaller)\n"
        "• 💸 Payment or Membership Help → @Violet100xGem\n\n"
        "👇 Reach out anytime. We respond fast."
    )
    await update.message.reply_text(message, parse_mode=constants.ParseMode.MARKDOWN, disable_web_page_preview=True)

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

# ---------- Main ----------
def main():
    logging.basicConfig(level=logging.INFO)
    keep_alive()  # Start Flask server for UptimeRobot

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Register commands
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("buy", buy))
    app.add_handler(CommandHandler("subscribe", subscribe))
    app.add_handler(CommandHandler("join", join))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("support", support))

    # Inline buttons (if any)
    app.add_handler(CallbackQueryHandler(button_callback))

    logging.info("🚀 Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
