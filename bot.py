import os
import logging
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, constants
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler, ContextTypes,
    MessageHandler, filters
)

from sheets import log_user
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# Load environment variables
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
MEMBERSHIP_LINK = "https://t.me/onlysubsbot?start=bXeGHtzWUbduBASZemGJf"
ADMIN_ID = 7906225936
BANNER_URL = "https://imgur.com/a/zwGFK7w"  # Confirmed correct

# Get all user IDs from Google Sheets
def get_all_user_ids():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name("service_account.json", scope)
    client = gspread.authorize(creds)

    sheet = client.open("SmartWalletsLog").sheet1
    user_ids = sheet.col_values(2)[1:]  # ✅ Column B (index 2), skip header
    return list(set([int(uid) for uid in user_ids if uid.isdigit()]))


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
    "⚡️ *30+ instant alerts daily* with token metrics & tap-to-copy CA\n"
    "🔗 Quick access to charts, bots, and trading tools\n"
    "🤖 Our bot Tracks *1,000+ elite wallets* with $1B+ total PnL\n"
    "📈 Multiple *100x+ calls posted in our main channel Solana100xcall*\n\n"
    "🎁 *Membership Bonuses:*\n"
    "• *Monthly:* 100 top wallets ($1M+ PnL), tagged & ready to import into *Axiom, BullX, Gmgn*, or any DEX\n"
    "• *Lifetime:* 300 pro wallets for full smart money visibility & long-term edge\n\n"
    "👇 Choose your plan and catch the next 100x"
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
    await context.bot.send_photo(
        chat_id=update.effective_user.id,
        photo="https://imgur.com/a/7ozHApz"
    )

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

    await context.bot.send_message(
        chat_id=update.effective_user.id,
        text=text,
        reply_markup=keyboard,
        parse_mode=constants.ParseMode.MARKDOWN
    )

async def show_pro(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_photo(
        chat_id=update.effective_user.id,
        photo="https://imgur.com/a/7VW8cqH"
    )

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔐 Pay with Crypto", url="https://whop.com/solana100xcall-smartwallets-300")],
        [InlineKeyboardButton("💳 Pay with Card", url="https://whop.com/solana100xcall-smartwallets-300")],
        [InlineKeyboardButton("⬅️ Return to Menu", callback_data="go_home")]
    ])

    text = (
        "👑 *Pro Trader Wallet Pack*\n\n"
        "Gain access to *300+ smart wallets* used by elite Solana traders.\n"
        "📈 Plug them into *Axiom, BullX, Gmgn*, or any wallet tracking tool.\n\n"
        "🧠 This is how pro traders catch the next 100x — before the herd.\n\n"
        "👇 Choose your access plan:"
    )

    await context.bot.send_message(
        chat_id=update.effective_user.id,
        text=text,
        reply_markup=keyboard,
        parse_mode=constants.ParseMode.MARKDOWN
    )

async def show_howsignals(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_photo(
        chat_id=update.effective_chat.id,
        photo="https://imgur.com/a/IiUPMt8"  # replace if different
    )

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
    await update.callback_query.message.reply_text(
        message,
        reply_markup=keyboard,
        parse_mode=constants.ParseMode.MARKDOWN,
        disable_web_page_preview=True
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

async def subscribe_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🚀 Get VIP Signals", url=MEMBERSHIP_LINK)],
        [InlineKeyboardButton("📲 Join Free Channel", url="https://t.me/Solana100xcall")]
    ])

    await update.message.reply_text(
        "🚀 *Unlock Full Access to VIP Signals*\n\n"
        "Get real-time alerts powered by AI & smart wallet tracking.\n"
        "Includes:\n"
        "• 30+ premium calls daily\n"
        "• Auto CA detection\n"
        "• 100+ elite wallets monitored\n\n"
        "🎯 First-mover advantage starts here.",
        parse_mode=constants.ParseMode.MARKDOWN,
        reply_markup=keyboard,
        disable_web_page_preview=True
    )

# Step 1: Ask for the broadcast content
async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ You are not authorized.")
        return

    await update.message.reply_text("✏️ Send the message you want to broadcast. You can also attach an image.")
    context.user_data["awaiting_broadcast"] = True

# Step 2: Handle the content and confirm
async def handle_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get("awaiting_broadcast"):
        return

    context.user_data["awaiting_broadcast"] = False
    context.user_data["broadcast_message"] = update.message

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Send to All Users", callback_data="confirm_broadcast"),
            InlineKeyboardButton("❌ Cancel", callback_data="cancel_broadcast")
        ]
    ])

    await update.message.reply_text("📢 Preview your message. Ready to send?", reply_markup=keyboard)

# Step 3: Confirm and send the message to all users
async def confirm_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    original = context.user_data.get("broadcast_message")
    if not original:
        await query.edit_message_text("⚠️ No message stored for broadcast.")
        return

    user_ids = get_all_user_ids()
    count = 0
    for user_id in user_ids:
        try:
            await context.bot.copy_message(
                chat_id=user_id,
                from_chat_id=original.chat.id,
                message_id=original.message_id
            )
            count += 1
        except Exception as e:
            logging.warning(f"Failed to send to {user_id}: {e}")

    await query.edit_message_text(f"✅ Broadcast sent to {count} users.")

# Step 4: Cancel broadcast
async def cancel_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    await update.callback_query.edit_message_text("🚫 Broadcast cancelled.")

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

    # ➕ Add standard command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("subscribe", subscribe_command))

    # ✅ Broadcast system for admin
    application.add_handler(CommandHandler("broadcast", broadcast))  # Trigger
    application.add_handler(MessageHandler(filters.ALL & filters.User(ADMIN_ID), handle_broadcast))  # Admin reply
    application.add_handler(CallbackQueryHandler(confirm_broadcast, pattern="^confirm_broadcast$"))  # Confirm
    application.add_handler(CallbackQueryHandler(cancel_broadcast, pattern="^cancel_broadcast$"))  # Cancel

    # 📲 Inline button logic
    application.add_handler(CallbackQueryHandler(button_handler))

    logging.info("Bot is running...")
    application.run_polling()

if __name__ == "__main__":
    main()
