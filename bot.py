from dotenv import load_dotenv
load_dotenv()

# -------------------------------
# Solana100xCall Membership Bot
# Tier System: Starter / Pro / Elite
# -------------------------------

# Standard libs
import os, logging, csv, json, asyncio, datetime
from datetime import datetime as dt, timezone
from pathlib import Path

# Third-party
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, constants
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler, ContextTypes,
    MessageHandler, filters
)
from telegram.error import Forbidden, BadRequest, RetryAfter, NetworkError, TelegramError
import httpx

from sheets import log_user
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# -------- Config --------
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "6793425735"))
BANNER_PATH = Path(__file__).parent / "assets" / "banner.png"
BANNER_FILE_ID = "AgACAgQAAxkDAAEgUPZp04yOXVC29QcONSf6UEeJJRMElAACmAxrG0fcoFLjzmAOtbn14QEAAwIAA3cAAzsE"

# -------- Tier payment links (replace placeholders when ready) --------
STARTER_LINK = "https://t.me/onlysubsbot?start=STARTER_PLACEHOLDER"
PRO_LINK     = "https://t.me/onlysubsbot?start=PRO_PLACEHOLDER"
ELITE_LINK   = "https://t.me/onlysubsbot?start=bXeGHtzWUbduBASZemGJf"

# -------- Tier pricing --------
STARTER_PRICE = 29
PRO_PRICE     = 44
ELITE_PRICE   = 59

# -------- Broadcast logging helpers --------
BASE_DIR = Path(os.getenv("DATA_DIR", ".")).resolve()
LOGS_DIR = BASE_DIR / "logs"
BACKUPS_DIR = BASE_DIR / "backups"
SUPPRESSION_PATH = BASE_DIR / "suppression.csv"

LOGS_DIR.mkdir(parents=True, exist_ok=True)
BACKUPS_DIR.mkdir(parents=True, exist_ok=True)


def _load_suppressed_ids() -> set[int]:
    s = set()
    if SUPPRESSION_PATH.exists():
        with open(SUPPRESSION_PATH, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                try:
                    s.add(int(row["user_id"]))
                except Exception:
                    continue
    return s

def _append_suppression(rows: list[dict]):
    if not rows:
        return
    write_header = not SUPPRESSION_PATH.exists()
    with open(SUPPRESSION_PATH, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["user_id","reason","date_added"])
        if write_header:
            w.writeheader()
        w.writerows(rows)

def _backup_users_csv_json(user_ids: list[int]):
    ts = datetime.datetime.now().strftime("%Y-%m-%d_%H%M%S")
    folder = BACKUPS_DIR / ts
    folder.mkdir(parents=True, exist_ok=True)
    csv_path = folder / "users_backup.csv"
    json_path = folder / "users_backup.json"
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["user_id"])
        for uid in user_ids:
            w.writerow([uid])
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump([{"user_id": uid} for uid in user_ids], f, ensure_ascii=False, indent=2)
    return folder

def _open_log_writer():
    ts = datetime.datetime.now().strftime("%Y-%m-%d_%H%M%S")
    log_path = LOGS_DIR / f"broadcast_{ts}.csv"
    f = open(log_path, "w", newline="", encoding="utf-8")
    w = csv.DictWriter(f, fieldnames=["user_id","status","error","timestamp"])
    w.writeheader()
    return f, w, log_path

def get_all_user_ids():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds_json = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")
    if not creds_json:
        raise ValueError("GOOGLE_SERVICE_ACCOUNT_JSON is missing from environment variables.")
    creds_dict = json.loads(creds_json)
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    sheet = client.open("SmartWalletsLog").sheet1
    user_ids = sheet.col_values(2)[1:]
    return list({int(uid.strip()) for uid in user_ids if uid and uid.strip().isdigit()})


# -------- Banner helper --------
async def send_banner(bot, chat_id: int):
    try:
        await bot.send_photo(chat_id=chat_id, photo=BANNER_FILE_ID)
        return
    except Exception as e:
        logging.warning(f"[banner] file_id send failed: {e}, trying local file")
    try:
        if BANNER_PATH.exists():
            with open(BANNER_PATH, "rb") as f:
                await bot.send_photo(chat_id=chat_id, photo=f)
            return
    except Exception as e:
        logging.warning(f"[banner] local send failed: {e}")


# -------- /start --------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    asyncio.create_task(
        asyncio.to_thread(log_user, user.id, user.first_name, user.username)
    )

    payload = context.args[0] if context.args else None
    logging.info(f"[START] User {user.id} (@{user.username}) joined with payload: {payload}")

    await context.bot.send_message(chat_id=ADMIN_ID, text=(
        f"{user.first_name} (@{user.username}) (#u{user.id}) has just launched this bot for the first time.\n\n"
        "You can send a private message to this member by replying to this message."
    ))

    await send_banner(context.bot, user.id)

    message = (
        "🚀 <b>Solana100xCall | Premium Signals</b>\n\n"
        "Real-time Solana signals powered by smart wallets.\n\n"
        "<b>What's Inside:</b>\n"
        "· Sniper Signals — ultra-early entries\n"
        "· ALPHA Signals — best daily opportunities\n"
        "· APEX Signals — peak confirmation\n"
        "· Milestone Tracker — live profit updates\n"
        "· VIP Trader Chat\n\n"
        "30+ daily signals\n"
        "100+ verified 10x–100x calls\n"
        "300+ active traders\n\n"
        "───────────────────────\n"
        f"🟢 Starter — ${STARTER_PRICE}/mo\n"
        f"🔵 Pro — ${PRO_PRICE}/mo\n"
        f"🟣 Elite — ${ELITE_PRICE}/mo\n\n"
        "👇 Choose your plan below."
    )

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("💎 View Membership Plans", callback_data="view_memberships")],
        [InlineKeyboardButton("💬 Member Testimonials", callback_data="show_testimonials")],
        [InlineKeyboardButton("👁 Live Signals Preview", callback_data="show_signals_preview")],
        [InlineKeyboardButton("Join FREE Main Channel", url="https://t.me/Solana100xcall")],
        [InlineKeyboardButton("🏆 100x+ Call Gallery", url="https://solana100xcall.fun/")],
        [
            InlineKeyboardButton("Help Bot", url="https://t.me/MyPremiumHelpBot"),
            InlineKeyboardButton("Contact Support", callback_data="show_support")
        ]
    ])

    menu_msg = await context.bot.send_message(
        chat_id=user.id,
        text=message,
        parse_mode=constants.ParseMode.HTML,
        reply_markup=keyboard,
        disable_web_page_preview=True
    )
    context.chat_data["menu_message_id"] = menu_msg.message_id
    context.chat_data["menu_chat_id"] = menu_msg.chat.id


# -------- View Memberships --------
async def show_memberships(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "💎 <b>Membership Plans</b>\n\n"

        f"🟢 <b>STARTER</b> — ${STARTER_PRICE}/mo\n"
        "Ideal for traders looking to get in early on every move.\n"
        "✅ Sniper Signals — ultra-early entries\n"
        "✅ Instant alerts\n"
        "✅ 500 Smart Wallets\n\n"

        f"🔵 <b>PRO</b> — ${PRO_PRICE}/mo\n"
        "Ideal for traders who want full signal coverage and deeper market insight.\n"
        "✅ Everything in Starter, plus:\n"
        "✅ ALPHA Signals\n"
        "✅ Milestone Tracker\n"
        "✅ 1,000 Smart Wallets\n\n"

        f"🟣 <b>ELITE</b> — ${ELITE_PRICE}/mo\n"
        "Ideal for traders who operate at the highest level and want every edge available.\n"
        "✅ Everything in Pro, plus:\n"
        "✅ APEX Signals\n"
        "✅ VIP Trader Chat\n"
        "✅ 2,000 Smart Wallets\n\n"

        "Select a plan to learn more."
    )

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(f"🟢 Starter | ${STARTER_PRICE}/month", callback_data="plan_starter")],
        [InlineKeyboardButton(f"🔵 Pro | ${PRO_PRICE}/month  ·  [POPULAR]", callback_data="plan_pro")],
        [InlineKeyboardButton(f"🟣 Elite | ${ELITE_PRICE}/month", callback_data="plan_elite")],
        [InlineKeyboardButton("Compare Plans", callback_data="compare_plans")],
        [InlineKeyboardButton("Payment Info", callback_data="payment_info")],
        [InlineKeyboardButton("← Back to Menu", callback_data="go_home")]
    ])

    await update.callback_query.answer()
    await update.callback_query.edit_message_text(
        text=text,
        reply_markup=keyboard,
        parse_mode=constants.ParseMode.HTML,
        disable_web_page_preview=True
    )


# -------- Plan detail pages --------
async def show_starter(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "🟢 <b>Starter — $29/mo</b>\n"
        "Ideal for traders looking to get in early on every move.\n\n"
        "<b>What's Included:</b>\n"
        "✅ Sniper Signals — ultra-early entries\n"
        "✅ Instant alerts — real-time notifications\n"
        f"🎁 500 Smart Wallets — import-ready for Axiom, Padre, GMGN\n\n"
        "50+ signals daily\n"
        "⚡ Instant buy buttons on every signal\n\n"
        "Tap below to get started."
    )

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🌐 Pay with SOL / BNB / ETH", callback_data="coming_soon")],
        [InlineKeyboardButton("← Back to Plans", callback_data="view_memberships")]
    ])

    await update.callback_query.answer()
    await update.callback_query.edit_message_text(
        text=text,
        reply_markup=keyboard,
        parse_mode=constants.ParseMode.HTML,
        disable_web_page_preview=True
    )


async def show_pro(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "🔵 <b>Pro — $44/mo</b>\n"
        "Ideal for traders who want full signal coverage and deeper market insight.\n\n"
        "<b>What's Included:</b>\n"
        "✅ Sniper Signals — ultra-early entries\n"
        "✅ ALPHA Signals — best daily opportunities\n"
        "✅ Instant alerts — real-time notifications\n"
        "✅ Milestone Tracker — live profit updates\n"
        f"🎁 1,000 Smart Wallets — import-ready for Axiom, Padre, GMGN\n\n"
        "30+ signals daily\n"
        "⚡ Instant buy buttons on every signal\n\n"
        "Tap below to get started."
    )

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🌐 Pay with SOL / BNB / ETH", callback_data="coming_soon")],
        [InlineKeyboardButton("← Back to Plans", callback_data="view_memberships")]
    ])

    await update.callback_query.answer()
    await update.callback_query.edit_message_text(
        text=text,
        reply_markup=keyboard,
        parse_mode=constants.ParseMode.HTML,
        disable_web_page_preview=True
    )


async def show_elite(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "🟣 <b>Elite — $59/mo</b>\n"
        "Ideal for traders who operate at the highest level and want every edge available.\n\n"
        "<b>What's Included:</b>\n"
        "✅ Sniper Signals — ultra-early entries\n"
        "✅ ALPHA Signals — best daily opportunities\n"
        "✅ APEX Signals — peak confirmation\n"
        "✅ Instant alerts — real-time notifications\n"
        "✅ Milestone Tracker — live profit updates\n"
        "✅ VIP Trader Chat\n"
        f"🎁 2,000 Smart Wallets — import-ready for Axiom, Padre, GMGN\n\n"
        "30+ signals daily\n"
        "⚡ Instant buy buttons on every signal\n\n"
        "Tap below to get started."
    )

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🌐 Pay with SOL / BNB / ETH", url=ELITE_LINK)],
        [InlineKeyboardButton("← Back to Plans", callback_data="view_memberships")]
    ])

    await update.callback_query.answer()
    await update.callback_query.edit_message_text(
        text=text,
        reply_markup=keyboard,
        parse_mode=constants.ParseMode.HTML,
        disable_web_page_preview=True
    )


# -------- Compare Plans --------
async def compare_plans(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "📊 <b>Compare Plans</b>\n\n"
        "<pre>"
        "Feature              | Starter | Pro  | Elite\n"
        "─────────────────────────────────────────────\n"
        "Sniper Signals       |   ✅   |  ✅  |  ✅\n"
        "ALPHA Signals        |   ❌   |  ✅  |  ✅\n"
        "APEX Signals         |   ❌   |  ❌  |  ✅\n"
        "Milestone Tracker    |   ❌   |  ✅  |  ✅\n"
        "VIP Trader Chat      |   ❌   |  ❌  |  ✅\n"
        "Smart Wallets        |   500  | 1,000| 2,000\n"
        "─────────────────────────────────────────────\n"
        f"Price/mo             |   ${STARTER_PRICE}  |  ${PRO_PRICE}  |  ${ELITE_PRICE}\n"
        "</pre>\n\n"
        "<b>Quick take:</b>\n"
        f"Starter ${STARTER_PRICE} — early entries, low commitment\n"
        f"Pro ${PRO_PRICE} — best value, full signal coverage\n"
        f"Elite ${ELITE_PRICE} — maximum data + community access\n\n"
        "Choose your plan below."
    )

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(f"🟢 Starter | ${STARTER_PRICE}/month", url=STARTER_LINK)],
        [InlineKeyboardButton(f"🔵 Pro | ${PRO_PRICE}/month  ·  [POPULAR]", url=PRO_LINK)],
        [InlineKeyboardButton(f"🟣 Elite | ${ELITE_PRICE}/month", url=ELITE_LINK)],
        [InlineKeyboardButton("← Back to Plans", callback_data="view_memberships")]
    ])

    await update.callback_query.answer()
    await update.callback_query.edit_message_text(
        text=text,
        reply_markup=keyboard,
        parse_mode=constants.ParseMode.HTML,
        disable_web_page_preview=True
    )


# -------- Payment Info --------
async def payment_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "💳 <b>Payment & Access</b>\n\n"
        "<b>Payment Methods:</b>\n"
        "Solana (SOL)\n"
        "Ethereum (ETH)\n"
        "Binance Coin (BNB)\n\n"
        "<b>How It Works:</b>\n"
        "1. Choose your plan below\n"
        "2. Complete payment via Payments bot\n"
        "3. Get instant access (30–60 seconds)\n\n"
        "<b>Privacy:</b>\n"
        "No KYC required\n"
        "Anonymous payments accepted\n"
        "Your data is never shared\n\n"
        "<b>Support:</b>\n"
        "Payment issues? @The100xMooncaller\n"
        "General help? @MyPremiumHelpBot\n\n"
        "Ready to join?"
    )

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(f"🟢 Starter | ${STARTER_PRICE}/month", url=STARTER_LINK)],
        [InlineKeyboardButton(f"🔵 Pro | ${PRO_PRICE}/month  ·  [POPULAR]", url=PRO_LINK)],
        [InlineKeyboardButton(f"🟣 Elite | ${ELITE_PRICE}/month", url=ELITE_LINK)],
        [InlineKeyboardButton("← Back to Plans", callback_data="view_memberships")]
    ])

    await update.callback_query.answer()
    await update.callback_query.edit_message_text(
        text=text,
        reply_markup=keyboard,
        parse_mode=constants.ParseMode.HTML,
        disable_web_page_preview=True
    )


# -------- Signals Preview --------
async def show_signals_preview(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "📊 <b>Live Signals Preview</b>\n\n"
        "This is what you'll receive:\n\n"
        "⚡ <b>ALPHA SIGNAL EXAMPLE:</b>\n"
        "<pre>"
        "⚡ ALPHA ALERT\n"
        "Smart money moving NOW\n\n"
        "$CTO | CA: BkQucpTXB2d...\n\n"
        "💎 MC: $69.21K  💧 Liq: $20.54K\n"
        "💵 Price: $0.00006921\n"
        "📊 Vol 5m: $0  ⏰ 1h: $204.62K\n"
        "👥 Holders: 804  📈 Trades: 6208\n"
        "⏰ Age: 1m  🔥 LP Burn: 0%\n\n"
        "💰 Smart-Money InFlow:\n"
        "33 tracked wallets bought (last 1m)\n"
        "Total Inflow: 68.44 SOL\n\n"
        "📱 Trojan Bot  •  Bloom  •  GMGN Bot\n"
        "🌐 Axiom  •  Padre  •  Dexscreener\n"
        "</pre>\n\n"
        "🏆 <b>MILESTONE UPDATE EXAMPLE:</b>\n"
        "<pre>"
        "🏆 UPDATE\n"
        "$CTO REACHED 14.3x\n\n"
        "CA: BkQucpTXB2d...\n\n"
        "🚀 Entry MC: $69.21K\n"
        "💎 Current MC: $989K\n"
        "🏆 ROI: 14.3x\n"
        "</pre>\n\n"
        "⚡ <b>What You Get:</b>\n"
        "• 50+ signals daily\n"
        "• Complete token metrics\n"
        "• Smart money inflow data\n"
        "• Instant Telegram bot buttons\n"
        "• Live milestone tracking\n\n"
        "👇 Get full access now"
    )

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("💎 View Plans", callback_data="view_memberships")],
        [InlineKeyboardButton("⬅️ Back to Menu", callback_data="go_home")]
    ])

    await update.callback_query.answer()
    await update.callback_query.edit_message_text(
        text=text,
        reply_markup=keyboard,
        parse_mode=constants.ParseMode.HTML,
        disable_web_page_preview=True
    )


# -------- How Signals Work --------
async def show_howsignals(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = (
        "📊 <b>How It Works</b>\n\n"
        "We send you alerts when opportunities appear.\n\n"
        "<b>Sniper Signals:</b>\n"
        "Ultra-early entries before momentum builds\n\n"
        "<b>ALPHA Signals:</b>\n"
        "Best daily opportunities with high potential\n\n"
        "<b>APEX Signals:</b>\n"
        "Peak confirmation with strong validation\n\n"
        "<b>Milestone Tracker:</b>\n"
        "Live updates when tokens hit 3x, 6x, 9x+\n\n"
        "<b>Each Signal Includes:</b>\n"
        "Token info (CA, price, liquidity)\n"
        "Instant buy buttons\n"
        "Chart links\n\n"
        "30+ quality signals daily\n"
        "100+ verified 10x–100x calls\n"
        "300+ active traders\n\n"
        "Ready to join?"
    )

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("View Plans", callback_data="view_memberships")],
        [InlineKeyboardButton("🏆 100x+ Call Gallery", url="https://solana100xcall.fun/")],
        [InlineKeyboardButton("← Back to Menu", callback_data="go_home")]
    ])

    if update.callback_query:
        await update.callback_query.answer()
        try:
            await update.callback_query.edit_message_text(
                text=message, reply_markup=keyboard,
                parse_mode=constants.ParseMode.HTML, disable_web_page_preview=True
            )
        except Exception:
            await context.bot.send_message(
                chat_id=update.callback_query.message.chat.id,
                text=message, reply_markup=keyboard,
                parse_mode=constants.ParseMode.HTML, disable_web_page_preview=True
            )
    else:
        if update.message:
            try: await update.message.delete()
            except Exception: pass
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=message, reply_markup=keyboard,
            parse_mode=constants.ParseMode.HTML, disable_web_page_preview=True
        )


# -------- Testimonials --------
async def show_testimonials(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "💬 <b>What Members Say</b>\n\n"
        "⭐⭐⭐⭐⭐ <i>\"Hit 3 calls over 10x in 2 months\"</i>\n"
        "\"Best signal service on Solana. The milestone tracker "
        "alone is worth it — I can see moves developing in real-time.\"\n"
        "— @AIAlphaKing\n\n"
        "⭐⭐⭐⭐⭐ <i>\"Paid for itself in week 1\"</i>\n"
        "\"Caught a Sniper signal that did 18x. My membership "
        "paid for itself with ONE call. Insane value.\"\n"
        "— @Violet100xGem\n\n"
        "⭐⭐⭐⭐⭐ <i>\"Finally, not exit liquidity\"</i>\n"
        "\"Most signal groups are just pump and dumps. Here you're "
        "getting real alpha. Makes all the difference.\"\n"
        "— @IamDreamer920\n\n"
        "⭐⭐⭐⭐⭐ <i>\"30+ signals DAILY is insane\"</i>\n"
        "\"Other groups send 5–10 signals per day. Here you get "
        "30+ QUALITY alerts. More opportunities = more wins.\"\n"
        "— @RooneyCryptoPolar\n\n"
        "<b>The Numbers:</b>\n"
        "300+ active members\n"
        "100+ verified 10x–100x calls\n"
        "30+ signals daily\n\n"
        "Join them today."
    )

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("View Plans", callback_data="view_memberships")],
        [InlineKeyboardButton("← Back", callback_data="go_home")]
    ])

    await update.callback_query.answer()
    await update.callback_query.edit_message_text(
        text=text, reply_markup=keyboard,
        parse_mode=constants.ParseMode.HTML, disable_web_page_preview=True
    )


# -------- Support --------
async def support(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = (
        "💬 <b>Contact Support</b>\n\n"
        "Please read before messaging.\n\n"
        "<b>I personally handle only:</b>\n"
        "Payment or billing issues\n"
        "Access problems to VIP channels\n"
        "Serious business or partnership inquiries\n\n"
        "<b>I do NOT reply to:</b>\n"
        "Win-rate or guarantees\n"
        "Scam accusations or low-effort messages\n"
        "System analysis or reverse-engineering\n\n"
        "For general questions use the help bot\n"
        "@MyPremiumHelpBot\n\n"
        "Direct support\n"
        "@The100xMooncaller"
    )

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("← Return to Menu", callback_data="go_home")]
    ])

    await update.callback_query.answer()
    await update.callback_query.edit_message_text(
        text=message, reply_markup=keyboard,
        parse_mode=constants.ParseMode.HTML, disable_web_page_preview=True
    )


# -------- Help --------
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = (
        "🆘 <b>Help</b>\n\n"
        "<b>What this bot does:</b>\n"
        "Shows membership plans and prices\n"
        "Processes your payment\n"
        "Gives instant access to signals\n\n"
        "<b>Membership Tiers:</b>\n"
        f"🟢 Starter | ${STARTER_PRICE}/month — Sniper Signals + 500 Wallets\n"
        f"🔵 Pro | ${PRO_PRICE}/month — + ALPHA Signals + Milestone Tracker\n"
        f"🟣 Elite | ${ELITE_PRICE}/month — + APEX Signals + VIP Chat\n\n"
        "<b>Need help?</b>\n"
        "General questions: @MyPremiumHelpBot\n"
        "Payment issues: Contact Support (main menu)\n"
    )

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("← Return to Menu", callback_data="go_home")]
    ])

    if update.callback_query:
        await update.callback_query.answer()
        try:
            await update.callback_query.edit_message_text(
                text=message, reply_markup=keyboard,
                parse_mode=constants.ParseMode.HTML, disable_web_page_preview=True
            )
        except Exception:
            await context.bot.send_message(
                chat_id=update.effective_chat.id, text=message,
                reply_markup=keyboard, parse_mode=constants.ParseMode.HTML,
                disable_web_page_preview=True
            )
    else:
        if update.message:
            try: await update.message.delete()
            except Exception: pass
        await context.bot.send_message(
            chat_id=update.effective_chat.id, text=message,
            reply_markup=keyboard, parse_mode=constants.ParseMode.HTML,
            disable_web_page_preview=True
        )


# -------- Subscribe / Join commands --------
async def subscribe_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("View All Plans", callback_data="view_memberships")],
        [InlineKeyboardButton("🏆 100x+ Call Gallery", url="https://solana100xcall.fun/")],
        [InlineKeyboardButton("Join Free Channel", url="https://t.me/Solana100xcall")],
        [InlineKeyboardButton("← Return to Menu", callback_data="go_home")]
    ])

    text = (
        "💳 <b>Subscribe</b>\n\n"
        "Choose your plan:\n\n"
        f"🟢 <b>Starter</b> | ${STARTER_PRICE}/month\n"
        f"🔵 <b>Pro</b> | ${PRO_PRICE}/month  ·  [POPULAR]\n"
        f"🟣 <b>Elite</b> | ${ELITE_PRICE}/month\n\n"
        "Instant access after payment."
    )

    if update.callback_query:
        await update.callback_query.answer()
        try:
            await update.callback_query.edit_message_text(
                text=text, reply_markup=keyboard,
                parse_mode=constants.ParseMode.HTML, disable_web_page_preview=True
            )
        except Exception:
            await context.bot.send_message(
                chat_id=update.callback_query.message.chat.id,
                text=text, reply_markup=keyboard,
                parse_mode=constants.ParseMode.HTML, disable_web_page_preview=True
            )
    else:
        if update.message:
            try: await update.message.delete()
            except Exception: pass
        await context.bot.send_message(
            chat_id=update.effective_chat.id, text=text,
            reply_markup=keyboard, parse_mode=constants.ParseMode.HTML,
            disable_web_page_preview=True
        )


async def join_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await subscribe_command(update, context)


# -------- Main Menu --------
async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = (
        "🚀 <b>Solana100xCall | Premium Signals</b>\n\n"
        "Real-time Solana signals powered by smart wallets.\n\n"
        "<b>What's Inside:</b>\n"
        "· Sniper Signals — ultra-early entries\n"
        "· ALPHA Signals — best daily opportunities\n"
        "· APEX Signals — peak confirmation\n"
        "· Milestone Tracker — live profit updates\n"
        "· VIP Trader Chat\n\n"
        "30+ daily signals\n"
        "100+ verified 10x–100x calls\n"
        "300+ active traders\n\n"
        "───────────────────────\n"
        f"🟢 Starter — ${STARTER_PRICE}/mo\n"
        f"🔵 Pro — ${PRO_PRICE}/mo\n"
        f"🟣 Elite — ${ELITE_PRICE}/mo\n\n"
        "👇 Choose your plan below."
    )

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("💎 View Membership Plans", callback_data="view_memberships")],
        [InlineKeyboardButton("💬 Member Testimonials", callback_data="show_testimonials")],
        [InlineKeyboardButton("👁 Live Signals Preview", callback_data="show_signals_preview")],
        [InlineKeyboardButton("Join FREE Main Channel", url="https://t.me/Solana100xcall")],
        [InlineKeyboardButton("🏆 100x+ Call Gallery", url="https://solana100xcall.fun/")],
        [
            InlineKeyboardButton("Help Bot", url="https://t.me/MyPremiumHelpBot"),
            InlineKeyboardButton("Contact Support", callback_data="show_support")
        ]
    ])

    if update.callback_query:
        query = update.callback_query
        await query.answer()
        try:
            await query.edit_message_text(
                text=message, reply_markup=keyboard,
                parse_mode=constants.ParseMode.HTML, disable_web_page_preview=True
            )
        except Exception:
            await context.bot.send_message(
                chat_id=query.message.chat.id, text=message,
                reply_markup=keyboard, parse_mode=constants.ParseMode.HTML,
                disable_web_page_preview=True
            )
    else:
        chat_id = update.effective_chat.id
        if update.message:
            try: await update.message.delete()
            except Exception: pass
        await context.bot.send_message(
            chat_id=chat_id, text=message, reply_markup=keyboard,
            parse_mode=constants.ParseMode.HTML, disable_web_page_preview=True
        )


# -------- Button handler --------
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query

    if query.data == "coming_soon":
        await query.answer("This plan is coming soon. For now, check out Elite.", show_alert=True)
        return

    await query.answer()

    if query.data == "go_home":
        await show_main_menu(update, context)
    elif query.data == "view_memberships":
        await show_memberships(update, context)
    elif query.data == "plan_starter":
        await show_starter(update, context)
    elif query.data == "plan_pro":
        await show_pro(update, context)
    elif query.data == "plan_elite":
        await show_elite(update, context)
    elif query.data == "show_support":
        await support(update, context)
    elif query.data == "show_howsignals":
        await show_howsignals(update, context)
    elif query.data == "show_testimonials":
        await show_testimonials(update, context)
    elif query.data == "show_signals_preview":
        await show_signals_preview(update, context)
    elif query.data == "compare_plans":
        await compare_plans(update, context)
    elif query.data == "payment_info":
        await payment_info(update, context)


# -------- Broadcast system --------
async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ You are not authorized.")
        return
    await update.message.reply_text("✏️ Send the message you want to broadcast. You can also attach an image.")
    context.user_data["awaiting_broadcast"] = True

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

async def confirm_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    original = context.user_data.get("broadcast_message")
    if not original:
        await query.edit_message_text("⚠️ No message stored for broadcast.")
        return

    try:
        user_ids = get_all_user_ids()
    except Exception as e:
        await query.edit_message_text(f"❌ Audience fetch failed: {e}")
        return

    _backup_users_csv_json(user_ids)
    suppressed = _load_suppressed_ids()

    log_file, log_writer, log_path = _open_log_writer()
    counts = {
        "delivered": 0, "delivered_after_retry": 0, "blocked": 0,
        "deleted_or_invalid": 0, "skipped_suppressed": 0, "network_error": 0, "error": 0
    }
    new_suppressed_rows = []
    lock = asyncio.Lock()

    CONCURRENCY = 20
    PACE_DELAY = 0.05
    sem = asyncio.Semaphore(CONCURRENCY)

    async def log_row(uid: int, status: str, err: str = ""):
        async with lock:
            ts = datetime.datetime.now().isoformat(timespec="seconds")
            log_writer.writerow({"user_id": uid, "status": status, "error": err, "timestamp": ts})

    async def send_one(uid: int):
        if uid in suppressed:
            async with lock:
                counts["skipped_suppressed"] += 1
            await log_row(uid, "skipped_suppressed")
            return

        async with sem:
            await asyncio.sleep(PACE_DELAY)
            try:
                await context.bot.copy_message(
                    chat_id=uid, from_chat_id=original.chat.id, message_id=original.message_id
                )
                async with lock:
                    counts["delivered"] += 1
                await log_row(uid, "delivered")

            except RetryAfter as e:
                await asyncio.sleep(int(getattr(e, "retry_after", 5)))
                try:
                    await context.bot.copy_message(
                        chat_id=uid, from_chat_id=original.chat.id, message_id=original.message_id
                    )
                    async with lock:
                        counts["delivered_after_retry"] += 1
                    await log_row(uid, "delivered_after_retry")
                except Exception as e2:
                    async with lock:
                        counts["error"] += 1
                    await log_row(uid, "error", f"RetryAfter-> {e2}")

            except Forbidden as e:
                msg = str(e).lower()
                reason = "deleted_or_invalid" if "deactivated" in msg else "blocked"
                async with lock:
                    counts[reason] += 1
                    new_suppressed_rows.append({
                        "user_id": uid, "reason": reason,
                        "date_added": datetime.date.today().isoformat()
                    })
                await log_row(uid, reason, str(e))

            except NetworkError as e:
                async with lock:
                    counts["network_error"] += 1
                await log_row(uid, "network_error", str(e))

            except Exception as e:
                async with lock:
                    counts["error"] += 1
                await log_row(uid, "error", str(e))

    total = len(user_ids)
    progress_msg = await query.edit_message_text(f"📤 Sending… 0/{total}")

    BATCH = 200
    tasks = []
    for i, uid in enumerate(user_ids, 1):
        tasks.append(asyncio.create_task(send_one(uid)))
        if i % BATCH == 0:
            await asyncio.sleep(0.1)
            sent = sum(counts.values())
            try:
                await progress_msg.edit_text(f"📤 Sending… {sent}/{total}")
            except Exception:
                pass

    await asyncio.gather(*tasks)

    log_file.close()
    _append_suppression(new_suppressed_rows)

    def _pct(n, d):
        return f"{(n/d*100):.1f}%" if d else "0%"

    total_sent = sum(counts.values())
    summary = (
        "✅ Broadcast complete\n"
        f"• delivered: {counts['delivered']}\n"
        f"• delivered_after_retry: {counts['delivered_after_retry']}\n"
        f"• blocked: {counts['blocked']}\n"
        f"• deleted_or_invalid: {counts['deleted_or_invalid']}\n"
        f"• skipped_suppressed: {counts['skipped_suppressed']}\n"
        f"• network_error: {counts['network_error']}\n"
        f"• error: {counts['error']}\n\n"
        f"% delivered: {_pct(counts['delivered'], total_sent)}\n"
        f"% blocked: {_pct(counts['blocked'], total_sent)}\n"
        f"🧾 Log saved: {log_path}"
    )
    await progress_msg.edit_text(summary)

async def cancel_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    await update.callback_query.edit_message_text("🚫 Broadcast cancelled.")


# -------- Admin log utils --------
def _latest_log_path():
    try:
        paths = sorted(LOGS_DIR.glob("broadcast_*.csv"))
        return paths[-1] if paths else None
    except Exception:
        return None

async def lastlog(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    p = _latest_log_path()
    if not p:
        await update.message.reply_text("No logs found yet.")
        return
    await context.bot.send_document(chat_id=ADMIN_ID, document=open(p, "rb"), filename=p.name, caption=f"🧾 Latest log: {p}")

async def broadcast_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    p = _latest_log_path()
    if not p:
        await update.message.reply_text("No logs found to summarize.")
        return
    import csv
    total = 0
    counts = {"delivered":0,"delivered_after_retry":0,"blocked":0,"deleted_or_invalid":0,"skipped_suppressed":0,"network_error":0,"error":0}
    with open(p, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            total += 1
            status = row.get("status","")
            if status in counts:
                counts[status] += 1
    def pct(n):
        return f"{(n/total*100):.1f}%" if total else "0%"
    msg = (
        f"🧮 Summary for {p.name}\n"
        f"• total rows: {total}\n"
        f"• delivered: {counts['delivered']}  ({pct(counts['delivered'])})\n"
        f"• delivered_after_retry: {counts['delivered_after_retry']}  ({pct(counts['delivered_after_retry'])})\n"
        f"• blocked: {counts['blocked']}  ({pct(counts['blocked'])})\n"
        f"• deleted_or_invalid: {counts['deleted_or_invalid']}  ({pct(counts['deleted_or_invalid'])})\n"
        f"• skipped_suppressed: {counts['skipped_suppressed']}  ({pct(counts['skipped_suppressed'])})\n"
        f"• network_error: {counts['network_error']}  ({pct(counts['network_error'])})\n"
        f"• error: {counts['error']}  ({pct(counts['error'])})\n"
    )
    await update.message.reply_text(msg)


# -------- Main --------
def main():
    logging.basicConfig(level=logging.INFO)
    application = Application.builder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("subscribe", subscribe_command))
    application.add_handler(CommandHandler("join", join_command))

    application.add_handler(CommandHandler("lastlog", lastlog))
    application.add_handler(CommandHandler("broadcast_stats", broadcast_stats))

    application.add_handler(CommandHandler("broadcast", broadcast))
    application.add_handler(
        MessageHandler(
            filters.User(ADMIN_ID) & (filters.TEXT | filters.PHOTO) & ~filters.COMMAND,
            handle_broadcast
        )
    )
    application.add_handler(CallbackQueryHandler(confirm_broadcast, pattern="^confirm_broadcast$"))
    application.add_handler(CallbackQueryHandler(cancel_broadcast, pattern="^cancel_broadcast$"))
    application.add_handler(CallbackQueryHandler(button_handler))

    logging.info("Bot is running...")
    application.run_polling()
    logging.info(f"[storage] BASE_DIR={BASE_DIR} LOGS_DIR={LOGS_DIR} BACKUPS_DIR={BACKUPS_DIR}")


if __name__ == "__main__":
    main()