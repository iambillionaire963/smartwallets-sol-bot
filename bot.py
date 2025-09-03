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
BANNER_URL = "https://imgur.com/a/cltw5k3"  # Confirmed correct

# Get all user IDs from Google Sheets
def get_all_user_ids():
    import json

    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds_json = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")

    if not creds_json:
        raise ValueError("GOOGLE_SERVICE_ACCOUNT_JSON is missing from environment variables.")

    creds_dict = json.loads(creds_json)
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)

    sheet = client.open("SmartWalletsLog").sheet1
    user_ids = sheet.col_values(2)[1:]  # ✅ Column B (index 2), skip header
    return list({int(uid.strip()) for uid in user_ids if uid and uid.strip().isdigit()})


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
"🚀 *Welcome to Premium Sniper Signals by Solana100xcall*\n\n"
"Hundreds of traders use our bot to catch Solana pumps 💥 before the hype inside the VIP group.\n\n"
"🤖 Filters 25,000+ tokens daily across Pumpfun, LetsBonk, Moonshot, and all launchpads.\n"
"⚡ Detects stealth launches, tracks smart inflows, and delivers top plays 24/7 ✅.\n\n"
"🎁 *Bonuses:*\n"
"🏆 1 Month: 100 smart money wallets\n"
"👑 Lifetime: TOP 500 smart money wallets\n\n"
"📦 Works with *BullX, Axiom, Padre, Gmgn*, or any DEX tool.\n\n"
"👇 Tap a plan below to join Premium."
)


    keyboard = InlineKeyboardMarkup([
    [InlineKeyboardButton("⚡ 1 Month Alpha Premium Access: $44.4", callback_data="plan_1month")],
    [InlineKeyboardButton("👑 Lifetime Alpha Premium Access: $111", callback_data="plan_lifetime")],
     [InlineKeyboardButton("🥇 Real Results (Phanes Verified)", url="https://t.me/Solana100xcallBoard")],
    [InlineKeyboardButton("📲 Join FREE Main Channel", url="https://t.me/Solana100xcall/4046")],
    [InlineKeyboardButton("📖 How Signals Work", callback_data="show_howsignals")],
    [InlineKeyboardButton("💬 Contact Support", callback_data="show_support")]
])

    await context.bot.send_message(
        chat_id=user.id,
        text=message,
        parse_mode=constants.ParseMode.MARKDOWN,
        reply_markup=keyboard,
        disable_web_page_preview=True
    )


async def show_howsignals(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_photo(
        chat_id=update.effective_chat.id,
        photo="https://imgur.com/a/IiUPMt8"  # replace if different
    )

    message = (
    "🧠 *How Signals Work*\n\n"
    "Our proprietary AI system continuously monitors 1,000+ elite Solana wallets with a combined PnL exceeding $1B.\n\n"
    "It captures real-time smart money activity across newly launched tokens, identifying:\n"
    "• 📥 Stealth entries from insiders\n"
    "• 💧 Liquidity movements and inflows\n"
    "• 🔍 On-chain volume shifts and wallet clusters\n\n"
    "Each alert is filtered by our algorithm for precision — removing noise, fake volume, and bait setups.\n\n"
    "⚙️ 100% autonomous execution\n"
    "⚡ Millisecond-grade detection and dispatch\n"
    "📡 24/7 live on-chain surveillance\n\n"
    "🔗 Need help or support? Message [@The100xMooncaller](https://t.me/The100xMooncaller)"
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
        "✅ Membership bonuses: smart wallets for BullX, Axiom, Padre, Gmgn\n\n"
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
async def show_1month(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_photo(chat_id=update.effective_user.id, photo=BANNER_URL)

    text = (
    "⚡ *1 Month Premium 🤝 $44.4*\n\n"
    "📈 30+ sniper alerts/day for fresh Solana memecoins\n"
    "🤖 AI scans 1,000+ smart wallets with $1B+ PnL\n"
    "📲 Instant CA, LP, volume, chart — no delay, no fluff\n"
    "🧠 Winning strategy that minimizes risk and maximizes gains\n\n"
    "🎁 Bonus: 100 smart money wallets (import-ready)\n"
    "🧠 Works with *BullX, Axiom, Padre, Gmgn* or any DEX\n\n"
    "💳 Tap below to unlock your access:"
)


    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🪙 Pay with Crypto", url=MEMBERSHIP_LINK)],
        [InlineKeyboardButton("⬅️ Return to Menu", callback_data="go_home")]
    ])

    await context.bot.send_message(
        chat_id=update.effective_user.id,
        text=text,
        parse_mode=constants.ParseMode.MARKDOWN,
        reply_markup=keyboard,
        disable_web_page_preview=True
    )


async def show_lifetime(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_photo(chat_id=update.effective_user.id, photo=BANNER_URL)

    text = (
    "👑 *Lifetime Premium 🤝 $111*\n\n"
    "📈 Unlimited access to AI-powered sniper signals\n"
    "🤖 Tracks 1,000+ elite wallets in real time\n"
    "📲 Auto CA, LP, volume, dev sold ⚡️ 100% filtered\n"
    "🧠 Winning strategy that minimizes risk and maximizes gains\n\n"
    "🎁 Bonus: 500 smart wallets (import-ready)\n"
    "🧠 For *BullX, Axiom, Padre, Gmgn* and advanced wallet tools\n\n"
    "💳 Tap below to unlock Lifetime access:"
)


    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🪙 Pay with Crypto", url=MEMBERSHIP_LINK)],
        [InlineKeyboardButton("⬅️ Return to Menu", callback_data="go_home")]
    ])

    await context.bot.send_message(
        chat_id=update.effective_user.id,
        text=text,
        parse_mode=constants.ParseMode.MARKDOWN,
        reply_markup=keyboard,
        disable_web_page_preview=True
    )

async def join_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🚀 Get VIP Signals", url=MEMBERSHIP_LINK)],
        [InlineKeyboardButton("📲 Join Free Channel", url="https://t.me/Solana100xcall")]
    ])

    await update.message.reply_text(
        "🚀 *Join the Premium Signal Group*\n\n"
        "Get AI-powered sniper calls based on 1,000+ smart wallets.\n\n"
        "🎯 Includes:\n"
        "• 30+ memecoin alerts daily\n"
        "• On-chain metrics & charts\n"
        "• Elite wallet tracking\n\n"
        "👇 Tap below to join:",
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
async def support(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = (
        "💬 *Contact Support*\n\n"
        "Need help with VIP access, signals, or smart wallets?\n"
        "Send a message to our support specialist:\n\n"
        "📩 [@The100xMooncaller](https://t.me/The100xMooncaller)\n\n"
        "We usually reply within minutes."
    )

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("⬅️ Return to Menu", callback_data="go_home")]
    ])

    await update.callback_query.message.reply_text(
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
    elif query.data == "show_support":
        await support(update, context)
    elif query.data == "go_home":
        await start(update, context)
    elif query.data == "plan_1month":
        await show_1month(update, context)
    elif query.data == "plan_lifetime":
        await show_lifetime(update, context)


# -------- Main --------

def main():
    logging.basicConfig(level=logging.INFO)
    application = Application.builder().token(BOT_TOKEN).build()

    # ➕ Add standard command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("subscribe", subscribe_command))
    application.add_handler(CommandHandler("join", join_command))


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