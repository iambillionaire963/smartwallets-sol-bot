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
        f"{user.first_name}🪐 (@{user.username}) (#u{user.id}) has just launched this bot for the first time.\n\n"
        "You can send a private message to this member by replying to this message."
    ))

    await context.bot.send_photo(chat_id=user.id, photo=BANNER_URL)

    message = (
        "🔒 *Premium Membership Includes:*\n\n"
        "✅ *30+ sniper-grade signals daily* — AI-powered, 24/7\n"
        "✅ *Instant alerts* with full info + Tap-to-Copy CA\n"
        "✅ *Private access to @The100xMooncaller* — Solana’s top memecoin trader\n\n"
        "🎁 *BONUS with Monthly Membership:* 100 elite wallets (PnL $1M+)\n"
        "🎁 *BONUS with Lifetime Membership:* 300+ elite wallets ready for BullX, Axiom, Gmgn, or any tracker\n\n"
        "👇 Choose your membership and start catching 10x plays:"
    )

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🚀 Get VIP Signals", url=MEMBERSHIP_LINK)],
        [InlineKeyboardButton("📲 Join FREE Main Channel", url="https://t.me/Solana100xcall")],
        [InlineKeyboardButton("📈 Latest Top Calls", url="https://t.me/Solana100xcall/4046")],
        [InlineKeyboardButton("📖 How Signals Work", callback_data="show_help")],
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
        [InlineKeyboardButton("💳 Pay with Card via WHOP", url="https://whop.com/solana100xcall-alpha")],
        [InlineKeyboardButton("⬅️ Return to Menu", callback_data="go_home")]
    ])

    text = (
        "💳 *Prefer to pay by card?*\n\n"
        "You can unlock VIP Memecoin Signals via *WHOP* — our secure payment partner.\n\n"
        "🏆 *Monthly Membership:* 100+ elite wallets + 30+ daily AI signals\n"
        "👑 *Alpha (1-Year/Lifetime):* 300+ elite wallets, lifetime tools & support\n\n"
        "👇 Choose your plan and start printing:"
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

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = (
        "🧠 *How it works*\n\n"
        "Our AI monitors thousands of the smartest wallets on Solana — with a combined PnL of over **$1B+**.\n"
        "These wallets consistently lead the biggest memecoin runs before anyone else.\n\n"
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

    await update.callback_query.message.edit_text(
        message, reply_markup=keyboard, parse_mode=constants.ParseMode.MARKDOWN, disable_web_page_preview=True
    )

async def support(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("💬 Chat with Support", url="https://t.me/The100xMooncaller")],
        [InlineKeyboardButton("⬅️ Return to Menu", callback_data="go_home")]
    ])

    await update.callback_query.message.edit_text(
        "🆘 *Support* 🆘\n\nReach out any time, we respond fast.",
        reply_markup=keyboard,
        parse_mode=constants.ParseMode.MARKDOWN
    )

async def join_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📲 Join the FREE main channel:
https://t.me/Solana100xcall"
    )

async def subscribe_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🚀 Choose your VIP membership:
" + MEMBERSHIP_LINK
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "show_help":
        await help_command(update, context)
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
