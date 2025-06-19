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
BANNER_URL = "https://imgur.com/a/LAr8QFT"
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
        "Unlock 2 elite tools trusted by top Solana traders:\n\n"
        "🧠 *Smart Wallets* — Track 300+ sniper, whale & insider wallets with *$1M+ average PnL*. Copy their trades. Plug them into BonkBot, Trojan, BullX & more.\n\n"
        "📈 *VIP Memecoin Signals* — Get real-time alerts on high-upside meme plays *before CT catches on*. AI-curated, wallet-verified.\n\n"
        "💰 Join 3,000+ traders already winning with our tools.\n\n"
        "👇 Tap below to explore:"
    )

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🚀 Get Premium Signals", url=MEMBERSHIP_LINK)],
        [InlineKeyboardButton("🧠 Smart Wallets Access", url="https://whop.com/solana100xcall-smartwallets-300")],
        [InlineKeyboardButton("📲 Join FREE Main Channel", url="https://t.me/Solana100xcall")],
        [InlineKeyboardButton("📈 Latest Top Calls", url="https://t.me/Solana100xcall/4046")],
        [InlineKeyboardButton("📖 How Signals Work", callback_data="show_help")],
        [InlineKeyboardButton("💳 Get VIP Membership", callback_data="show_buy")],
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

    text = "👉 To get started, click the button below, select your membership, and proceed to payment:"

    if update.callback_query:
        await update.callback_query.message.edit_text(
            text,
            reply_markup=keyboard,
            parse_mode=constants.ParseMode.MARKDOWN
        )
    else:
        await update.message.reply_text(
            text,
            reply_markup=keyboard,
            parse_mode=constants.ParseMode.MARKDOWN
        )

async def support(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("💬 Chat with Support", url="https://t.me/The100xMooncaller")],
        [InlineKeyboardButton("⬅️ Return to Menu", callback_data="go_home")]
    ])

    text = "🆘 *Support* 🆘\n\nReach out any time, we respond fast."

    if update.callback_query:
        await update.callback_query.message.edit_text(
            text,
            reply_markup=keyboard,
            parse_mode=constants.ParseMode.MARKDOWN
        )
    else:
        await update.message.reply_text(
            text,
            reply_markup=keyboard,
            parse_mode=constants.ParseMode.MARKDOWN
        )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = (
        "🧠 *How it works*\n\n"
        "Our AI monitors thousands of the smartest wallets on Solana — with a combined PnL of over **$1B+**. These wallets consistently lead the biggest memecoin runs before anyone else.\n\n"
        "We track their moves in real time and send you sniper-grade alerts with zero delays or noise.\n\n"
        "❓ FAQs:\n"
        "• Manual or automated? → Fully AI-powered. No human input.\n"
        "• Speed? → Instant alerts. No lag.\n"
        "• Alert timing? → Mostly during US market hours.\n\n"
        "Need support? Reach out anytime: [@The100xMooncaller](https://t.me/The100xMooncaller)"
    )

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🚀 Get Premium Access", url=MEMBERSHIP_LINK)],
        [InlineKeyboardButton("⬅️ Return to Menu", callback_data="go_home")]
    ])

    if update.callback_query:
        await update.callback_query.message.edit_text(
            message,
            parse_mode=constants.ParseMode.MARKDOWN,
            reply_markup=keyboard,
            disable_web_page_preview=True
        )
    else:
        await update.message.reply_text(
            message,
            parse_mode=constants.ParseMode.MARKDOWN,
            reply_markup=keyboard,
            disable_web_page_preview=True
        )

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

# -------- Main Entry Point --------

def main():
    logging.basicConfig(level=logging.INFO)
    application = Application.builder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("buy", buy))
    application.add_handler(CommandHandler("support", support))
    application.add_handler(CallbackQueryHandler(button_handler))

    logging.info("Bot is running...")
    application.run_polling()

if __name__ == "__main__":
    main()
