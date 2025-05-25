
import os
import logging
from flask import Flask
from threading import Thread
from telegram import Update, constants, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, CallbackQueryHandler
from sheets import log_user
# Log user to Google Sheets

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
ADMIN_ID = 7851863021  # 🔁 Replace with your actual Telegram ID

# ---------- Handlers ----------

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

BANNER_URL = "https://imgur.com/a/s3sS1Ld"  # Replace with your banner image URL

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    # ✅ Log user to Google Sheets (with error catch)
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

    # Send banner image first
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
    message = "👉 To get started, click the button below, select your membership, and proceed to payment:"
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🚀 Get Premium Access", url=MEMBERSHIP_LINK)],
        [InlineKeyboardButton("⬅️ Return to Menu", callback_data="go_home")]
    ])

    msg = update.message or update.callback_query.message
    await msg.reply_text(message, reply_markup=keyboard)

async def subscribe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = "🔥 Ready to unlock premium alerts?\n\nChoose your membership and activate full access now:"
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🚀 Get Premium Access", url=MEMBERSHIP_LINK)],
        [InlineKeyboardButton("⬅️ Return to Menu", callback_data="go_home")]
    ])
    await update.message.reply_text(message, reply_markup=keyboard)

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

from telegram.constants import ChatAction

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    # Only allow the admin to use this command
    if user_id != ADMIN_ID:
        await update.message.reply_text("❌ You are not authorized to use this command.")
        return

    # Check if there is a message to broadcast
    if not context.args:
        await update.message.reply_text("⚠️ Please provide a message to broadcast. Usage: /broadcast Your message here")
        return

    # Compose the message
    broadcast_text = " ".join(context.args)

    # Load your user list here (e.g. from a database or flat file)
    user_ids = []  # ← Fill this list with your member IDs

    count = 0
    for user_id in user_ids:
        try:
            await context.bot.send_chat_action(chat_id=user_id, action=ChatAction.TYPING)
            await context.bot.send_message(chat_id=user_id, text=broadcast_text)
            count += 1
        except Exception as e:
            logging.warning(f"Failed to send to {user_id}: {e}")

    await update.message.reply_text(f"✅ Broadcast sent to {count} users.")


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

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🚀 Get Premium Access", url=MEMBERSHIP_LINK)],
        [InlineKeyboardButton("⬅️ Return to Menu", callback_data="go_home")]
    ])

    msg = update.message or update.callback_query.message
    await msg.reply_text(
        message,
        parse_mode=constants.ParseMode.MARKDOWN,
        reply_markup=keyboard,
        disable_web_page_preview=True
    )

async def support(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = (
        "🆘 *Support* 🆘\n\n"
        "💬 *Need Help or Have Questions?*\n\n"
        "We're here to help you 24/7.\n\n"
        "• 👨‍💻 Tech/Access Issues → [@The100xMooncaller](https://t.me/The100xMooncaller)\n"
        "• 💸 Payment or Membership Help → @Violet100xGem\n\n"
        "👇 Reach out anytime. We respond fast.\n\n"
        "⬇️Contact our support by pressing the button below⬇️\n\n"
    )
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("💬 Chat with Support", url="https://t.me/The100xMooncaller")],
        [InlineKeyboardButton("⬅️ Return to Menu", callback_data="go_home")]
    ])

    msg = update.message or update.callback_query.message
    await msg.reply_text(message, parse_mode=constants.ParseMode.MARKDOWN, reply_markup=keyboard)

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "show_help":
        await help_command(update, context)

    elif query.data == "show_buy":
        await buy(update, context)

    elif query.data == "show_support":
        await support(update, context)

    elif query.data == "go_home":
        user = update.effective_user
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

# ---------- Main ----------
def main():
    logging.basicConfig(level=logging.INFO)
    keep_alive()  # Start Flask server for UptimeRobot

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Register commands
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("buy", buy))
    app.add_handler(CommandHandler("broadcast", broadcast))
    app.add_handler(CommandHandler("subscribe", subscribe))
    app.add_handler(CommandHandler("join", join))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("support", support))

    # Inline button callbacks
    app.add_handler(CallbackQueryHandler(button_callback))

    logging.info("🚀 Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
