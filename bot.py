import os
import logging
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, constants
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler, ContextTypes
)

from sheets import log_user  # your google sheets logging function

# Load environment variables
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
MEMBERSHIP_LINK = "https://t.me/onlysubsbot?start=bXeGHtzWUbduBASZemGJf"
ADMIN_ID = 7906225936
BANNER_URL = "https://imgur.com/a/s3sS1Ld"
WEBHOOK_URL_BASE = "https://telegram-premium-bot-qgqy.onrender.com"  # Your domain

# -------- Handlers --------

def build_membership_message() -> str:
    return (
        "👋 Welcome to Smart Wallets by Solana100xCall\n\n"
        "💰 Get access to sniper, insider & whale wallets with *$1B+ in profits.*\n"
        "🔗 Ready to import into *BullX, Axiom, Gmgn*\n"
        "👀 Copy trade them with *BonkBot, PepeBoost, Trojan*\n"
        "📈 Track them in *Cielo, Raybot, SpyBot*, and more.\n\n"
        "⚠️ Plus: unlock *Premium Alerts* based on wallet inflows, memecoin momentum, and smart money signals.\n\n"
        "🔥 *Join hundreds of traders making daily profits — tap /start to unlock the alpha and dominate Solana memecoins!*"
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
    await update.message.reply_text("🔥 Unlock premium alerts and insider access!\n\nChoose your membership below to start receiving exclusive real-time signals and whale wallet alerts:
", reply_markup=keyboard)

async def join(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton("📲 Join @Solana100xcall", url="https://t.me/Solana100xcall")]]
    await update.message.reply_text(
        "📢 *Stay ahead in Solana trading!*\n\n"
        "Join our *FREE public channel* to see the milestones reached on premium calls, promos, and exclusive previews of the smart alerts our AI delivers to Premium members.\n\n"
        "🔥 Thousands of traders already rely on this channel — tap below and join the community now:\n\n"
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
    user_ids = []  # You must fill this list with your users from your DB or sheet

    count = 0
    for user_id in user_ids:
        try:
            await context.bot.send_chat_action(chat_id=user_id, action="typing")
            await context.bot.send_message(chat_id=user_id, text=message)
            count += 1
        except Exception as e:
            logging.warning(f"Failed to send to {user_id}: {e}")

    await update.message.reply_text(f"✅ Broadcast sent to {count} users.")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = (
        "🧠 How it works\n\n"
        "Our AI monitors smart money wallets moving $100k+ weekly on Solana — delivering sniper-grade, real-time alerts with zero delays or noise.\n\n"
        "❓ FAQs:\n"
        "• Manual or automated? Fully AI-powered, no manual input.\n"
        "• Speed? Instant alerts, no lag.\n"
        "• Alert timing? Mostly during US market hours.\n\n"
        "Need support? Reach out anytime: [@The100xMooncaller](https://t.me/The100xMooncaller)"
    )
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🚀 Get Premium Access", url=MEMBERSHIP_LINK)],
        [InlineKeyboardButton("⬅️ Return to Menu", callback_data="go_home")]
    ])
    msg = update.message or update.callback_query.message
    await msg.reply_text(message, parse_mode=constants.ParseMode.MARKDOWN, reply_markup=keyboard, disable_web_page_preview=True)
    
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

# -------- Main --------

def main():
    logging.basicConfig(level=logging.INFO)
    application = Application.builder().token(BOT_TOKEN).build()

    # Command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("buy", buy))
    application.add_handler(CommandHandler("subscribe", subscribe))
    application.add_handler(CommandHandler("join", join))
    application.add_handler(CommandHandler("status", status))
    application.add_handler(CommandHandler("broadcast", broadcast))
    application.add_handler(CommandHandler("help", help_command))

    # CallbackQueryHandler for inline buttons
    application.add_handler(CallbackQueryHandler(button_handler))

    # Start polling updates from Telegram
    application.run_polling()

if __name__ == "__main__":
    main()

