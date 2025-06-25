import os
import logging
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, constants
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler, ContextTypes
)

from sheets import log_user

# Load environment variables
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
MEMBERSHIP_LINK = "https://t.me/onlysubsbot?start=bXeGHtzWUbduBASZemGJf"
ADMIN_ID = 7906225936
BANNER_URL = "https://imgur.com/a/LAr8QFT"  # Confirmed correct

# -------- Handlers --------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    try:
        log_user(user.id, user.first_name, user.username)
    except Exception as e:
        logging.warning(f"[Google Sheets] Failed to log user {user.id}: {e}")

    payload = context.args[0] if context.args else None
    logging.info(f"[START] User {user.id} (@{user.username}) joined with payload: {payload}")

    await context.bot.send_message(chat_id=ADMIN_ID, text=(
        f"{user.first_name}🎐 (@{user.username}) (#u{user.id}) has just launched this bot for the first time.\n\n"
        "You can send a private message to this member by replying to this message."
    ))

    await context.bot.send_photo(chat_id=user.id, photo=BANNER_URL)

    message = (
    "*Welcome to Solana100xcall Premium Bot* 🚀\n"
    "Get AI-powered sniper signals based on real-time smart money activity and on-chain data.\n\n"
    "⚡️ *30+ instant alerts daily* with full token info & tap-to-copy CA\n"
    "🤖 Tracks 1,000+ top wallets with $1B+ combined PnL\n"
    "📈 Multiple 100x+ calls, shared with full transparency\n"
    "🔗 Fast access to charts, trading bots, and tools\n\n"
    "🎁 *Bonuses:*\n"
    "Monthly = 100 elite wallets · Lifetime = 300 wallets for BullX, Axiom, Gmgn, and more\n\n"
    "👇 Choose your plan and start catching the next 10x:"
)

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🚀 Get VIP Signals", url=MEMBERSHIP_LINK)],
        [InlineKeyboardButton("📲 Join FREE Main Channel", url="https://t.me/Solana100xcall")],
        [InlineKeyboardButton("📈 Latest Top Calls", url="https://t.me/Solana100xcall/4046")],
        [InlineKeyboardButton("📖 How Signals Work", callback_data="show_howsignals")],
        [InlineKeyboardButton("💳 Pay VIP with Card", callback_data="show_card")],
        [InlineKeyboardButton("👑 Pro Trader Mode", callback_data="show_pro")],
        [InlineKeyboardButton("💬 Contact Support", callback_data="show_support")]
    ])

    await context.bot.send_message(
        chat_id=user.id,
        text=message,
        parse_mode=constants.ParseMode.MARKDOWN,
        reply_markup=keyboard,
        disable_web_page_preview=True
    )

async def show_card(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🏆 1-Month Access — Pay with Card", url="https://whop.com/solana100xcall-alpha")],
        [InlineKeyboardButton("👑 Lifetime Access — Pay with Card", url="https://whop.com/solana100xcall-alpha-1year")],
        [InlineKeyboardButton("⬅️ Return to Menu", callback_data="go_home")]
    ])

    text = (
        "💳 *Prefer to pay by card?*\n\n"
        "Get instant access to *VIP Memecoin Signals* via *WHOP*, our secure payment partner.\n\n"
        "🏆 *1-Month Membership:*\n"
        "✅ 30+ sniper-grade signals daily\n"
        "✅ 100+ elite wallets included\n\n"
        "👑 *Lifetime Membership:*\n"
        "✅ All monthly benefits\n"
        "✅ 300+ elite wallets for BullX, Axiom, Gmgn\n"
        "✅ Lifetime access, tools & support\n\n"
        "👇 Tap a plan to get started:"
    )

    await update.callback_query.message.edit_text(
        text, reply_markup=keyboard, parse_mode=constants.ParseMode.MARKDOWN
    )

async def show_pro(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔐 Pay with Crypto", url="https://whop.com/solana100xcall-smartwallets-300")],
        [InlineKeyboardButton("💳 Pay with Card", url="https://whop.com/solana100xcall-smartwallets-300")],
        [InlineKeyboardButton("⬅️ Return to Menu", callback_data="go_home")]
    ])

    text = (
        "👑 *Pro Trader Wallet Pack*\n\n"
        "Unlock *300+ elite wallets* used by top traders 📥 Import them into *BullX, Axiom, Gmgn* or track in any Telegram bot.\n\n"
        "See what whales are buying in real time.\n\n"
        "👇 Choose a payment option:"
    )

    await update.callback_query.message.edit_text(
        text, reply_markup=keyboard, parse_mode=constants.ParseMode.MARKDOWN
    )

async def show_howsignals(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = (
        "🧠 *How Signals Work*\n\n"
        "Our AI scans 1,000+ top Solana wallets with a combined PnL of $1B+.\n"
        "It detects early memecoin buys, trends, and inflows from smart money.\n\n"
        "You get sniper-grade alerts the moment smart wallets ape in — no delay, no fluff.\n\n"
        "✅ Fully automated\n"
        "⚡️ Real-time alerts\n"
        "🌎 24/7 global monitoring\n\n"
        "Need help? Message [@The100xMooncaller](https://t.me/The100xMooncaller)"
    )

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("⬅️ Return to Menu", callback_data="go_home")]
    ])

    await update.callback_query.message.edit_text(
        message,
        reply_markup=keyboard,
        parse_mode=constants.ParseMode.MARKDOWN,
        disable_web_page_preview=True
    )

async def support(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("💬 Chat with Support", url="https://t.me/The100xMooncaller")],
        [InlineKeyboardButton("⬅️ Return to Menu", callback_data="go_home")]
    ])

    await update.callback_query.message.edit_text(
        "🚘 *Support* 🚘\n\nReach out any time, we respond fast.",
        reply_markup=keyboard,
        parse_mode=constants.ParseMode.MARKDOWN
    )

async def join_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📲 Join the FREE main channel: https://t.me/Solana100xcall"
    )

async def subscribe_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🚀 Choose your VIP membership:\n" + MEMBERSHIP_LINK
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = (
        "🆘 *Need Help?*\n\n"
        "This bot delivers sniper-grade Solana memecoin signals based on:\n"
        "• On-chain wallet tracking (1,000+ smart wallets)\n"
        "• High-liquidity inflow detection\n"
        "• AI-powered trade pattern analysis\n\n"
        "You’ll receive:\n"
        "✅ Instant alerts with token data & copy-ready CAs\n"
        "✅ Membership bonuses: smart wallets for BullX, Axiom, Gmgn\n\n"
        "📬 For support, message [@The100xMooncaller](https://t.me/The100xMooncaller)"
    )

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("⬅️ Return to Menu", callback_data="go_home")]
    ])

    await update.message.reply_text(
        message,
        parse_mode=constants.ParseMode.MARKDOWN,
        reply_markup=keyboard,
        disable_web_page_preview=True
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "show_howsignals":
        await show_howsignals(update, context)
    elif query.data == "show_card":
        await show_card(update, context)
    elif query.data == "show_pro":
        await show_pro(update, context)
    elif query.data == "show_support":
        await support(update, context)
    elif query.data == "go_home":
        await start(update, context)

# -------- Main --------

def main():
    logging.basicConfig(level=logging.INFO)
    application = Application.builder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("join", join_command))
    application.add_handler(CommandHandler("subscribe", subscribe_command))
    application.add_handler(CallbackQueryHandler(button_handler))

    logging.info("Bot is running...")
    application.run_polling()

if __name__ == "__main__":
    main()
