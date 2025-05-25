import os
import logging
import asyncio
from flask import Flask, request

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, constants
from telegram.constants import ChatAction
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    ContextTypes
)

from sheets import log_user

# Load environment variable
BOT_TOKEN = os.getenv("BOT_TOKEN")
MEMBERSHIP_LINK = "https://t.me/onlysubsbot?start=bXeGHtzWUbduBASZemGJf"
ADMIN_ID = 7851863021  # Replace with your actual Telegram ID
BANNER_URL = "https://i.imgur.com/q9R7VYf.jpeg"  # ✅ Direct image link

# ---------- Flask for Keep-Alive ----------
app = Flask(__name__)

# Define the global Application instance early
application = Application.builder().token(BOT_TOKEN).build()

@app.post(f"/{BOT_TOKEN}")
async def webhook(request):
    if request.headers.get("content-type") == "application/json":
        data = await request.get_json()
        update = Update.de_json(data, application.bot)
        await application.process_update(update)
        return "OK", 200
    return "Invalid content type", 403

# ---------- Bot Handlers ----------

def build_membership_message() -> str:
    return (
        "🚀 *Welcome to Solana100xcall Premium Bot* 🚀\n\n"
        "💡 Solana’s smartest wallets. Tracked by AI. Calls Delivered in real time.\n\n"
        "⚡️ 30+ sniper-grade alerts daily\n"
        "📋 Tap-to-copy contracts — no fumbling\n"
        "💰 Find early low-cap plays before CT does\n"
        "🐋 Whale wallet tracking with AI-powered filters\n\n"
        "🔓 Choose your membership below and plug into real-time smart money flow.\n\n"
        "💬 Questions? DM [@The100xMooncaller](https://t.me/The100xMooncaller)\n"
        "📈 Track record: t.me/solana100xcall/4046\n\n"
        "🔒 Telegram access\n"
        "Quantum AI Memecoin Alerts By Solana100xcall 🫡"
    )

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    try:
        log_user(user.id, user.first_name, user.username)
    except Exception as e:
        logging.warning(f"[Google Sheets] Failed to log user {user.id}: {e}")

    payload = context.args[0] if context.args else None
    logging.info(f"[START] User {user.id} (@{user.username}) joined with payload: {payload}")

    first_name = user.first_name or "Unknown"
    username = f"@{user.username}" if user.username else "(no username)"
    display_name = f"{first_name}🪐 ({username})"
    user_code = f"#u{user.id}"
    admin_message = (
        f"{display_name} ({user_code}) has just launched this bot for the first time.\n\n"
        f"You can send a private message to this member by replying to this message."
    )
    await context.bot.send_message(chat_id=ADMIN_ID, text=admin_message)

    await context.bot.send_photo(chat_id=user.id, photo=BANNER_URL)

    message = (
        "🚀 *Welcome to Solana100xcall Premium Bot* 🚀\n\n"
        "💡 _Solana’s smartest wallets. Tracked by AI. Calls Delivered in real time._\n\n"
        "⚡️ 30+ sniper-grade alerts daily\n"
        "📋 Tap-to-copy contracts — no fumbling\n"
        "💰 Find early low-cap plays before CT does\n"
        "🐋 Whale wallet tracking with AI-powered filters\n\n"
        "This isn't crowdsourced noise. It's real-time data from million-dollar wallets.\n\n"
        "👇 Tap below to unlock the feed:"
    )

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🚀 Get Premium Signals", url=MEMBERSHIP_LINK)],
        [InlineKeyboardButton("📲 Join FREE Main Channel", url="https://t.me/Solana100xcall")],
        [InlineKeyboardButton("📈 Latest Top Calls", url="https://t.me/Solana100xcall/4046")],
        [InlineKeyboardButton("📖 How It Works", callback_data="show_help")],
        [InlineKeyboardButton("💳 Buy Membership", callback_data="show_buy")],
        [InlineKeyboardButton("💬 Contact Support", callback_data="show_support")]
    ])

    await context.bot.send_message(
        chat_id=user.id,
        text=message,
        parse_mode=constants.ParseMode.MARKDOWN,
        reply_markup=keyboard,
        disable_web_page_preview=True
    )

async def buy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🚀 Get Premium Access", url=MEMBERSHIP_LINK)],
        [InlineKeyboardButton("⬅️ Return to Menu", callback_data="go_home")]
    ])
    msg = update.message or update.callback_query.message
    await msg.reply_text("👉 To get started, click the button below, select your membership, and proceed to payment:", reply_markup=keyboard)

async def subscribe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🚀 Get Premium Access", url=MEMBERSHIP_LINK)],
        [InlineKeyboardButton("⬅️ Return to Menu", callback_data="go_home")]
    ])
    await update.message.reply_text("🔥 Ready to unlock premium alerts?\n\nChoose your membership and activate full access now:", reply_markup=keyboard)

async def join(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton("📲 Join @Solana100xcall", url="https://t.me/Solana100xcall")]]
    await update.message.reply_text(
        "📢 *Stay Ahead with Solana100xcall*\n\n"
        "Before you unlock Premium, join our *FREE public channel* to see why thousands trust our alpha.\n\n"
        "🔥 Live calls, charts, and sneak peeks into the exact kind of alerts our AI delivers to Premium members.\n\n"
        "👇 Tap below to join the official channel:",
        parse_mode=constants.ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(keyboard),
        disable_web_page_preview=True
    )

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Use /buy to view membership options.")

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ You are not authorized to use this command.")
        return

    if not context.args:
        await update.message.reply_text("⚠️ Please provide a message to broadcast. Usage: /broadcast Your message here")
        return

    message = " ".join(context.args)
    user_ids = []  # Populate this list from your data source (e.g., Google Sheet)

    count = 0
    for user_id in user_ids:
        try:
            await context.bot.send_chat_action(chat_id=user_id, action=ChatAction.TYPING)
            await context.bot.send_message(chat_id=user_id, text=message)
            count += 1
        except Exception as e:
            logging.warning(f"Failed to send to {user_id}: {e}")

    await update.message.reply_text(f"✅ Broadcast sent to {count} users.")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = (
        "🧠 *How It Works*\n"
        "Our AI tracks real-time smart money on Solana — wallets making $100k+ each week...\n\n"
        "❓ *Common Questions:*\n"
        "• Is this manual? → No. It’s 100% AI-powered.\n"
        "• Is this fast? → Yes. No delays. No crowdsourced nonsense.\n"
        "• Do alerts come at night? → Most during US trading hours.\n\n"
        "Need help? Message [@The100xMooncaller](https://t.me/The100xMooncaller)"
    )
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🚀 Get Premium Access", url=MEMBERSHIP_LINK)],
        [InlineKeyboardButton("⬅️ Return to Menu", callback_data="go_home")]
    ])
    msg = update.message or update.callback_query.message
    await msg.reply_text(message, parse_mode=constants.ParseMode.MARKDOWN, reply_markup=keyboard, disable_web_page_preview=True)

async def support(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("💬 Chat with Support", url="https://t.me/The100xMooncaller")],
        [InlineKeyboardButton("⬅️ Return to Menu", callback_data="go_home")]
    ])
    msg = update.message or update.callback_query.message
    await msg.reply_text("🆘 *Support* 🆘\n\nReach out any time, we respond fast.", parse_mode=constants.ParseMode.MARKDOWN, reply_markup=keyboard)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "show_help":
        await help_command(update, context)
    elif query.data == "show_buy":
        await buy(update, context)
    elif query.data == "show_support":
        await support(update, context)
    elif query.data == "go_home":
        await start(update, context)

# ---------- Main Entry ----------
def main():
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("buy", buy))
    application.add_handler(CommandHandler("subscribe", subscribe))
    application.add_handler(CommandHandler("join", join))
    application.add_handler(CommandHandler("status", status))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("support", support))
    application.add_handler(CommandHandler("broadcast", broadcast))
    application.add_handler(CallbackQueryHandler(button_handler))

    # Set webhook
    WEBHOOK_URL = f"https://telegram-premium-bot-qgqy.onrender.com/{BOT_TOKEN}"
    asyncio.run(application.bot.set_webhook(url=WEBHOOK_URL))

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
