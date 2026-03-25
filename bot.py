# -------------------------------
# Solana100xcall Membership Bot
# with Broadcast Logging + Suppression
# -------------------------------

# Standard libs
import os, logging, csv, json, asyncio, datetime
from pathlib import Path

# Third-party
from dotenv import load_dotenv
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

# Load environment variables
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
MEMBERSHIP_LINK = "https://t.me/onlysubsbot?start=bXeGHtzWUbduBASZemGJf"
ADMIN_ID = 7906225936
BANNER_PATH = Path(__file__).parent / "assets" / "banner.png"


# -------- Broadcast logging helpers (disk-aware for Render) --------
# If DATA_DIR is set (e.g., /var/data on Render), use it. Otherwise default to current folder.
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

# Get all user IDs from Google Sheets
def get_all_user_ids():
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

async def send_banner(bot, chat_id: int):
    """
    Sends the banner image safely:
    1) Try local file (most reliable).
    2) If BANNER_URL is set, download bytes, verify it's an image, and send.
    3) Fallback to sending a text link so the flow never crashes.
    """
    # 1) Local file first
    try:
        if BANNER_PATH.exists():
            with open(BANNER_PATH, "rb") as f:
                await bot.send_photo(chat_id=chat_id, photo=f)
            return
    except Exception as e:
        logging.warning(f"[banner] local send failed: {e}")

    # 2) Remote URL -> download bytes and validate content-type
    BANNER_URL = None  # Set to URL if needed
    if BANNER_URL:
        try:
            async with httpx.AsyncClient(follow_redirects=True, timeout=10) as client:
                r = await client.get(BANNER_URL)
                r.raise_for_status()
                ctype = r.headers.get("content-type", "")
                if not ctype.startswith("image/"):
                    raise ValueError(f"URL is not an image (content-type: {ctype})")
                await bot.send_photo(chat_id=chat_id, photo=r.content)
            return
        except (BadRequest, TelegramError, Exception) as e:
            logging.warning(f"[banner] url send failed: {e} (url={BANNER_URL})")

    # 3) Final fallback: plain link
    link_text = BANNER_URL or "banner image unavailable"
    await bot.send_message(chat_id=chat_id, text=f"🖼️ {link_text}")





# -------- Handlers --------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    # Log user in background (non-blocking) - makes /start instant
    asyncio.create_task(
        asyncio.to_thread(log_user, user.id, user.first_name, user.username)
    )

    payload = context.args[0] if context.args else None
    logging.info(f"[START] User {user.id} (@{user.username}) joined with payload: {payload}")

    await context.bot.send_message(chat_id=ADMIN_ID, text=(
        f"{user.first_name}🎐 (@{user.username}) (#u{user.id}) has just launched this bot for the first time.\n\n"
        "You can send a private message to this member by replying to this message."
    ))

    await send_banner(context.bot, user.id)

    message = (
        "🚀 Solana100xCall | Premium Signals\n\n"
        "The real alpha. No fluff.\n\n"
        "💎 What's Inside:\n"
        "🥷 Sniper Signals (ultra-early entries)\n"
        "⚡ ALPHA Signals (best daily opportunities)\n"
        "💎 APEX Signals (peak confirmation)\n"
        "🏆 Milestone Tracker (live profit updates)\n"
        "💬 VIP Trader Chat\n\n"
        "📊 30+ quality signals daily\n"
        "🏆 100+ verified 10x-100x calls\n"
        "👥 300+ active traders\n\n"
        "🔥 FLASH SALE | 50% OFF LIFETIME ONLY\n"
        "👑 Lifetime: $49 (was $99)\n"
        "⏰ Ends in 72 hours\n\n"
        "🔥 1 Month: $44 (20% off)\n"
        "💎 3 Months: $63 (20% off)\n\n"
        "👇 Choose your plan"
    )

    keyboard = InlineKeyboardMarkup([
    [InlineKeyboardButton("🔥 View Memberships", callback_data="view_memberships")],
    [InlineKeyboardButton("💬 Member Testimonials", callback_data="show_testimonials")],
    [InlineKeyboardButton("📊 See Live Signals Preview", callback_data="show_signals_preview")],
    [InlineKeyboardButton("📲 Join FREE Main Channel", url="https://t.me/Solana100xcall")],
    [InlineKeyboardButton("🏆 100x+ Call Gallery", url="https://solana100xcall.fun/")],
    [
        InlineKeyboardButton("🤖 Help Bot", url="https://t.me/MyPremiumHelpBot"),
        InlineKeyboardButton("💬 Contact Support", callback_data="show_support")
    ]
])

    menu_msg = await context.bot.send_message(
        chat_id=user.id,
        text=message,
        parse_mode=constants.ParseMode.MARKDOWN,
        reply_markup=keyboard,
        disable_web_page_preview=True
    )
    context.chat_data["menu_message_id"] = menu_msg.message_id
    context.chat_data["menu_chat_id"] = menu_msg.chat.id



async def show_howsignals(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = (
        "📊 *How It Works*\n\n"
        
        "We send you alerts when opportunities appear.\n\n"
        
        "🥷 *Sniper Signals:*\n"
        "Ultra-early entries before momentum builds\n\n"
        
        "⚡ *ALPHA Signals:*\n"
        "Best daily opportunities with high potential\n\n"
        
        "💎 *APEX Signals:*\n"
        "Peak confirmation with strong validation\n\n"
        
        "🏆 *Milestone Tracker:*\n"
        "Live updates when tokens hit 3x, 6x, 9x+\n\n"
        
        "📊 *Each Signal Includes:*\n"
        "• Token info (CA, price, liquidity)\n"
        "• Instant buy buttons\n"
        "• Chart links\n\n"
        
        "⚡ 30+ quality signals daily\n"
        "🏆 100+ verified 10x-100x calls\n"
        "👥 300+ active traders\n\n"
        
        "👇 Ready to join?"
    )
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🚀 Get Access Now", callback_data="view_memberships")],
        [InlineKeyboardButton("🏆 View 100x Gallery", url="https://solana100xcall.fun/")],
        [InlineKeyboardButton("⬅️ Back to Menu", callback_data="go_home")]
    ])

    if update.callback_query:
        await update.callback_query.answer()
        try:
            await update.callback_query.edit_message_text(
                text=message,
                reply_markup=keyboard,
                parse_mode=constants.ParseMode.MARKDOWN,
                disable_web_page_preview=True
            )
        except Exception:
            await context.bot.send_message(
                chat_id=update.callback_query.message.chat.id,
                text=message,
                reply_markup=keyboard,
                parse_mode=constants.ParseMode.MARKDOWN,
                disable_web_page_preview=True
            )
    else:
        if update.message:
            try: await update.message.delete()
            except Exception: pass
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=message,
            reply_markup=keyboard,
            parse_mode=constants.ParseMode.MARKDOWN,
            disable_web_page_preview=True
        )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = (
        "🆘 *Help*\n\n"
        "*What this bot does:*\n"
        "🔹 Shows membership plans and prices\n"
        "🔹 Processes your payment\n"
        "🔹 Gives instant access to signals\n\n"
        "*What you'll receive:*\n"
        "🥷 Sniper Signals (early entries)\n"
        "⚡ ALPHA Signals (best opportunities)\n"
        "💎 APEX Signals (peak confirmation)\n"
        "🏆 Milestone Tracker (live updates)\n"
        "💬 Active Trader Chat\n\n"
        "*Need help?*\n"
        "🤖 General questions: @MyPremiumHelpBot\n"
        "💳 Payment issues: Contact Support (main menu)\n"
    )

    keyboard = InlineKeyboardMarkup(
        [[InlineKeyboardButton("⬅️ Return to Menu", callback_data="go_home")]]
    )

    if update.callback_query:
        await update.callback_query.answer()
        try:
            await update.callback_query.edit_message_text(
                text=message,
                reply_markup=keyboard,
                parse_mode=constants.ParseMode.MARKDOWN,
                disable_web_page_preview=True
            )
        except Exception:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=message,
                reply_markup=keyboard,
                parse_mode=constants.ParseMode.MARKDOWN,
                disable_web_page_preview=True
            )
    else:
        if update.message:
            try:
                await update.message.delete()
            except Exception:
                pass
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=message,
            reply_markup=keyboard,
            parse_mode=constants.ParseMode.MARKDOWN,
            disable_web_page_preview=True
        )


async def subscribe_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🚀 Get Access", url=MEMBERSHIP_LINK)],
        [InlineKeyboardButton("🏆 100x+ Call Gallery", url="https://solana100xcall.fun/")],
        [InlineKeyboardButton("📲 Join Free Channel", url="https://t.me/Solana100xcall")],
        [InlineKeyboardButton("⬅️ Return to Menu", callback_data="go_home")]
    ])

    text = (
    "💳 *Subscribe*\n\n"
    "Choose your plan:\n"
    "🔥 1 Month: $44\n"
    "💎 3 Months: $63\n"
    "👑 Lifetime: $49 (FLASH SALE)\n\n"
    "*What's Included:*\n"
    "🥷 Sniper Signals (early entries)\n"
    "⚡ ALPHA Signals (best opportunities)\n"
    "💎 APEX Signals (peak confirmation)\n"
    "🏆 Milestone Tracker (live updates)\n"
    "💬 Active Trader Chat\n\n"
    "🎁 *Bonus:*\n"
    "Elite wallets (300-1000 depending on plan)\n"
    "Import-ready for Axiom, Padre, GMGN\n\n"
    "⚡ Instant access after payment"
)



    if update.callback_query:
        await update.callback_query.answer()
        try:
            await update.callback_query.edit_message_text(
                text=text,
                reply_markup=keyboard,
                parse_mode=constants.ParseMode.MARKDOWN,
                disable_web_page_preview=True
            )
            context.chat_data["menu_message_id"] = update.callback_query.message.message_id
            context.chat_data["menu_chat_id"] = update.callback_query.message.chat.id
        except Exception:
            menu_msg = await context.bot.send_message(
                chat_id=update.callback_query.message.chat.id,
                text=text,
                reply_markup=keyboard,
                parse_mode=constants.ParseMode.MARKDOWN,
                disable_web_page_preview=True
            )
            context.chat_data["menu_message_id"] = menu_msg.message_id
            context.chat_data["menu_chat_id"] = menu_msg.chat.id
    else:
        if update.message:
            try:
                await update.message.delete()
            except Exception:
                pass

        chat_id = update.effective_chat.id
        menu_id = context.chat_data.get("menu_message_id")
        menu_chat = context.chat_data.get("menu_chat_id", chat_id)

        if menu_id:
            try:
                await context.bot.edit_message_text(
                    chat_id=menu_chat,
                    message_id=menu_id,
                    text=text,
                    reply_markup=keyboard,
                    parse_mode=constants.ParseMode.MARKDOWN,
                    disable_web_page_preview=True
                )
            except Exception:
                menu_msg = await context.bot.send_message(
                    chat_id=chat_id,
                    text=text,
                    reply_markup=keyboard,
                    parse_mode=constants.ParseMode.MARKDOWN,
                    disable_web_page_preview=True
                )
                context.chat_data["menu_message_id"] = menu_msg.message_id
                context.chat_data["menu_chat_id"] = menu_msg.chat.id
        else:
            menu_msg = await context.bot.send_message(
                chat_id=chat_id,
                text=text,
                reply_markup=keyboard,
                parse_mode=constants.ParseMode.MARKDOWN,
                disable_web_page_preview=True
            )
            context.chat_data["menu_message_id"] = menu_msg.message_id
            context.chat_data["menu_chat_id"] = menu_msg.chat.id


async def show_signals_preview(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "📊 *Live Signals Preview*\n\n"
        
        "This is what you'll receive:\n\n"
        
        "⚡ *ALPHA SIGNAL EXAMPLE:*\n"
        "```\n"
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
        "🌐 Scanners: SolHacker | TTF | Trenchy\n\n"
        "📱 Telegram Trading Bots:\n"
        "Trojan Bot  •  Bloom  •  GMGN Bot\n\n"
        "🌐 Dex/Scanners:\n"
        "Trojan Terminal  •  Axiom  •  Padre\n"
        "GMGN Web  •  Dexscreener  •  MobyScreener\n"
        "```\n\n"
        
        "🏆 *MILESTONE UPDATE EXAMPLE:*\n"
        "```\n"
        "🏆 UPDATE\n"
        "$CTO REACHED 14.3x\n\n"
        "CA: BkQucpTXB2d...\n\n"
        "🚀 Entry MC: $69.21K\n"
        "💎 Current MC: $989K\n"
        "🏆 ROI: 14.3x\n\n"
        "📱 Telegram Trading Bots:\n"
        "Trojan Bot  •  Bloom  •  GMGN Bot\n\n"
        "🌐 Dex/Scanners:\n"
        "Trojan Terminal  •  Axiom  •  Dexscreener\n"
        "```\n\n"
        
        "⚡ *What You Get:*\n"
        "• 30+ premium signals daily\n"
        "• Complete token metrics\n"
        "• Smart money inflow data\n"
        "• Instant Telegram bot buttons\n"
        "• Direct dex/scanner links\n"
        "• Live milestone tracking\n\n"
        
        "👇 Get full access now"
    )
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🚀 Subscribe Now", url=MEMBERSHIP_LINK)],
        [InlineKeyboardButton("⬅️ Back", callback_data="go_home")]
    ])
    
    await update.callback_query.edit_message_text(
        text=text,
        reply_markup=keyboard,
        parse_mode=constants.ParseMode.MARKDOWN,
        disable_web_page_preview=True
    )

async def compare_plans(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "📊 *Compare Plans*\n\n"

        "🔥 *FLASH SALE: Lifetime 50% OFF (72h only)*\n\n"

        "```\n"
        "Feature          | 1M | 3M | LT\n"
        "─────────────────┼────┼────┼────\n"
        "Sniper Signals   | ✅ | ✅ | ✅\n"
        "ALPHA Signals    | ✅ | ✅ | ✅\n"
        "Milestone Track  | ✅ | ✅ | ✅\n"
        "Trader Chat      | ✅ | ✅ | ✅\n"
        "Elite Wallets    |300 |500 | 2K\n"
        "Future Updates   | ❌ | ❌ | ✅\n"
        "Never Pay Again  | ❌ | ❌ | ✅\n"
        "Price (NOW)      |$44 |$63 |$49\n"
        "```\n\n"

        "💰 *Cost Breakdown:*\n"
        "• 1 Month: $44/month\n"
        "• 3 Months: $21/month\n"
        "• Lifetime: $49 ONE TIME (then $0/month forever)\n\n"

        "💡 *Quick Math:*\n"
        "Lifetime at $49 vs 3-Month at $63?\n"
        "→ Pay LESS for lifetime access\n"
        "→ Save $14 immediately + never pay again\n"
        "→ Get 4x more wallets (2,000 vs 500)\n\n"

        "🏆 *No-Brainer:*\n"
        "Lifetime is cheaper than 3-Month right now.\n"
        "⏰ Price increases in 72 hours.\n\n"
        
        "👇 Choose your plan"
    )
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔥 1 Month | $44", url=MEMBERSHIP_LINK)],
        [InlineKeyboardButton("💎 3 Months | $63 (POPULAR)", url=MEMBERSHIP_LINK)],
        [InlineKeyboardButton("👑 Lifetime | $49 (FLASH SALE)", url=MEMBERSHIP_LINK)],
        [InlineKeyboardButton("⬅️ Back", callback_data="view_memberships")]
    ])

    await update.callback_query.edit_message_text(
        text=text,
        reply_markup=keyboard,
        parse_mode=constants.ParseMode.MARKDOWN,
        disable_web_page_preview=True
    )

async def payment_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "💳 *Payment & Access*\n\n"
        
        "💳 *Payment Methods:*\n"
        "✅ Solana (SOL)\n"
        "✅ Ethereum (ETH)\n"
        "✅ Binance Coin (BNB)\n\n"
        
        "⚡ *How It Works:*\n"
        "1. Choose your plan\n"
        "2. Complete payment via Payments bot\n"
        "3. Get instant access (30-60 seconds)\n\n"
        
        "🔐 *Privacy:*\n"
        "✅ No KYC required\n"
        "✅ Anonymous payments accepted\n"
        "✅ Your data is never shared\n\n"
        
        "⚡ *What You Get:*\n"
        "After payment, instant access to:\n"
        "• All signal channels\n"
        "• VIP trader chat\n"
        "• Elite wallets bonus\n\n"
        
        "💬 *Support:*\n"
        "Payment issues? @The100xMooncaller\n"
        "General help? @MyPremiumHelpBot\n\n"
        
        "👇 Ready to join?"
    )
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🚀 Subscribe Now", url=MEMBERSHIP_LINK)],
        [InlineKeyboardButton("⬅️ Back", callback_data="view_memberships")]  # ← CAMBIO
    ])
    
    await update.callback_query.edit_message_text(
        text=text,
        reply_markup=keyboard,
        parse_mode=constants.ParseMode.MARKDOWN,
        disable_web_page_preview=True
    )

async def roi_calculator(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "💰 *ROI Calculator*\n\n"
        
        "How fast can you break even?\n\n"
        
        "📊 *SCENARIO 1: Conservative*\n"
        "Lifetime: $49\n"
        "Your typical trade: $100\n"
        "You need: ONE 1x (token doubles)\n"
        "→ You profit: $100 (membership paid + $21 profit)\n\n"
        
        "📊 *SCENARIO 2: Realistic*\n"
        "Lifetime: $49\n"
        "Your typical trade: $500\n"
        "You need: ONE 20% gain\n"
        "→ You profit: $100 (membership paid + $21 profit)\n\n"
        
        "📊 *SCENARIO 3: Our Track Record*\n"
        "100+ calls hit 10x+\n"
        "Catch just ONE with $200:\n"
        "→ Your $200 becomes $2,000\n"
        "→ Profit: $1,800\n"
        "→ ROI: 2,178%\n\n"
        
        "🎯 *Bottom Line:*\n"
        "You need ONE decent move\n"
        "to pay for membership forever.\n\n"
        
        "📈 *Daily Opportunities:*\n"
        "• 30+ quality signals per day\n"
        "• You only need 1-2 wins\n\n"
        
        "💡 *Simple Math:*\n"
        "Risk: $49 (one time)\n"
        "Upside: Unlimited opportunities\n"
        "Time to ROI: Usually first week\n\n"
        
        "👇 Get started"
    )
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🚀 Get Lifetime | $49", url=MEMBERSHIP_LINK)],
        [InlineKeyboardButton("💎 View All Plans", callback_data="view_memberships")],
        [InlineKeyboardButton("⬅️ Back", callback_data="go_home")]
    ])
    
    await update.callback_query.edit_message_text(
        text=text,
        reply_markup=keyboard,
        parse_mode=constants.ParseMode.MARKDOWN,
        disable_web_page_preview=True
    )

async def show_1month(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
    "🔥 <b>1 Month Access</b>\n"
    "<s>$55</s> → <b>$44</b> (20% OFF)\n\n"
    "<b>What's Included:</b>\n"
    "🥷 Sniper Signals (ultra-early entries)\n"
    "⚡ ALPHA Signals (best daily opportunities)\n"
    "💎 APEX Signals (peak confirmation)\n"
    "🏆 Milestone Tracker (live profit updates)\n"
    "💬 Active Trader Chat\n\n"
    "📊 30+ quality signals daily\n"
    "⚡ Instant buy buttons included\n\n"
    "🎁 <b>Bonus:</b> 300 elite wallets\n"
    "(import-ready for Axiom, Padre, GMGN)\n\n"
    "💳 Tap below to get started"
)


    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🪙 Pay with SOL / BNB / ETH", url=MEMBERSHIP_LINK)],
        [InlineKeyboardButton("⬅️ Back", callback_data="view_memberships")]  # ← CAMBIO
    ])

    await update.callback_query.edit_message_text(
        text=text,
        reply_markup=keyboard,
        parse_mode=constants.ParseMode.HTML,
        disable_web_page_preview=True
    )


async def show_3month(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
    "💎 <b>3 Months Access</b>\n"
    "<s>$79</s> → <b>$63</b> (20% OFF)\n\n"
    "<b>What's Included:</b>\n"
    "🥷 Sniper Signals (ultra-early entries)\n"
    "⚡ ALPHA Signals (best daily opportunities)\n"
    "💎 APEX Signals (peak confirmation)\n"
    "🏆 Milestone Tracker (live profit updates)\n"
    "💬 Active Trader Chat\n\n"
    "📊 30+ quality signals daily\n"
    "⚡ Instant buy buttons included\n\n"
    "🎁 <b>Bonus:</b> 500 elite wallets\n"
    "(import-ready for Axiom, Padre, GMGN)\n\n"
    "💡 <b>Best value:</b> Save 52% vs monthly plan\n\n"
    "💳 Tap below to get started"
)


    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🪙 Pay with SOL / BNB / ETH", url=MEMBERSHIP_LINK)],
        [InlineKeyboardButton("⬅️ Back", callback_data="view_memberships")]  # ← CAMBIO
    ])

    await update.callback_query.edit_message_text(
        text=text,
        reply_markup=keyboard,
        parse_mode=constants.ParseMode.HTML,
        disable_web_page_preview=True
    )

async def show_lifetime(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
    "👑 <b>Lifetime Access</b>\n"
    "<s>$99</s> → <b>$49</b> (50% OFF)\n\n"
    "🔥 <b>FLASH SALE | ENDS IN 72 HOURS</b>\n"
    "One payment. Never pay again.\n\n"
    "<b>What's Included:</b>\n"
    "🥷 Sniper Signals (ultra-early entries)\n"
    "⚡ ALPHA Signals (best daily opportunities)\n"
    "💎 APEX Signals (peak confirmation)\n"
    "🏆 Milestone Tracker (live profit updates)\n"
    "💬 Active Trader Chat\n\n"
    "📊 30+ quality signals daily\n"
    "⚡ Instant buy buttons included\n\n"
    "🎁 <b>EXCLUSIVE BONUS:</b> 2,000 elite wallets\n"
    "(import-ready for Trojan, Axiom, Padre, GMGN)\n\n"
    "♾️ All future updates included forever\n\n"
    "⏰ <b>This price ends in 72 hours</b>\n\n"
    "💳 Tap below to lock in $49 Lifetime"
)

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🪙 Pay with SOL / BNB / ETH", url=MEMBERSHIP_LINK)],
        [InlineKeyboardButton("⬅️ Back", callback_data="view_memberships")]  # ← CAMBIO
    ])

    await update.callback_query.edit_message_text(
        text=text,
        reply_markup=keyboard,
        parse_mode=constants.ParseMode.HTML,
        disable_web_page_preview=True
    )

    

async def join_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🚀 Get Access", url=MEMBERSHIP_LINK)],
        [InlineKeyboardButton("🏆 100x+ Call Gallery", url="https://solana100xcall.fun/")],
        [InlineKeyboardButton("📲 Join Free Channel", url="https://t.me/Solana100xcall")],
        [InlineKeyboardButton("⬅️ Return to Menu", callback_data="go_home")]
    ])

    text = (
    "💳 *Get Access*\n\n"
    "Choose your plan:\n"
    "🔥 1 Month: $44\n"
    "💎 3 Months: $63\n"
    "👑 Lifetime: $49 (FLASH SALE)\n\n"
    "*What's Included:*\n"
    "🥷 Sniper Signals (early entries)\n"
    "⚡ ALPHA Signals (best opportunities)\n"
    "💎 APEX Signals (peak confirmation)\n"
    "🏆 Milestone Tracker (live updates)\n"
    "💬 Active Trader Chat\n\n"
    "📊 30+ quality signals daily\n"
    "⚡ Instant buy buttons included\n\n"
    "⚡ Instant access after payment"
)


    if update.callback_query:
        await update.callback_query.answer()
        try:
            await update.callback_query.edit_message_text(
                text=text,
                reply_markup=keyboard,
                parse_mode=constants.ParseMode.MARKDOWN,
                disable_web_page_preview=True
            )
            context.chat_data["menu_message_id"] = update.callback_query.message.message_id
            context.chat_data["menu_chat_id"] = update.callback_query.message.chat.id
        except Exception:
            menu_msg = await context.bot.send_message(
                chat_id=update.callback_query.message.chat.id,
                text=text,
                reply_markup=keyboard,
                parse_mode=constants.ParseMode.MARKDOWN,
                disable_web_page_preview=True
            )
            context.chat_data["menu_message_id"] = menu_msg.message_id
            context.chat_data["menu_chat_id"] = menu_msg.chat.id
    else:
        if update.message:
            try:
                await update.message.delete()
            except Exception:
                pass

        chat_id = update.effective_chat.id
        menu_id = context.chat_data.get("menu_message_id")
        menu_chat = context.chat_data.get("menu_chat_id", chat_id)

        if menu_id:
            try:
                await context.bot.edit_message_text(
                    chat_id=menu_chat,
                    message_id=menu_id,
                    text=text,
                    reply_markup=keyboard,
                    parse_mode=constants.ParseMode.MARKDOWN,
                    disable_web_page_preview=True
                )
            except Exception:
                menu_msg = await context.bot.send_message(
                    chat_id=chat_id,
                    text=text,
                    reply_markup=keyboard,
                    parse_mode=constants.ParseMode.MARKDOWN,
                    disable_web_page_preview=True
                )
                context.chat_data["menu_message_id"] = menu_msg.message_id
                context.chat_data["menu_chat_id"] = menu_msg.chat.id
        else:
            menu_msg = await context.bot.send_message(
                chat_id=chat_id,
                text=text,
                reply_markup=keyboard,
                parse_mode=constants.ParseMode.MARKDOWN,
                disable_web_page_preview=True
            )
            context.chat_data["menu_message_id"] = menu_msg.message_id
            context.chat_data["menu_chat_id"] = menu_msg.chat.id



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

# Step 3: Confirm and send the message to all users  (with logs + suppression)
async def confirm_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    original = context.user_data.get("broadcast_message")
    if not original:
        await query.edit_message_text("⚠️ No message stored for broadcast.")
        return

    # 1) Fetch audience and make a backup
    try:
        user_ids = get_all_user_ids()
    except Exception as e:
        await query.edit_message_text(f"❌ Audience fetch failed: {e}")
        return

    _backup_users_csv_json(user_ids)
    suppressed = _load_suppressed_ids()

    # 2) Open log + counters
    log_file, log_writer, log_path = _open_log_writer()
    counts = {
        "delivered": 0,
        "delivered_after_retry": 0,
        "blocked": 0,
        "deleted_or_invalid": 0,
        "skipped_suppressed": 0,
        "network_error": 0,
        "error": 0
    }
    new_suppressed_rows = []
    lock = asyncio.Lock()  # protect shared counters/logs

    # 3) Concurrency + simple rate limit
    #    Telegram global safe budget ≈ ~28 msgs / sec. We'll cap concurrency and pace.
    CONCURRENCY = 20     # parallel workers
    PACE_DELAY = 0.05    # 50ms between sends per worker (~20/sec aggregate with concurrency)

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
            # light pacing to avoid spikes
            await asyncio.sleep(PACE_DELAY)
            try:
                await context.bot.copy_message(
                    chat_id=uid,
                    from_chat_id=original.chat.id,
                    message_id=original.message_id
                )
                async with lock:
                    counts["delivered"] += 1
                await log_row(uid, "delivered")

            except RetryAfter as e:
                await asyncio.sleep(int(getattr(e, "retry_after", 5)))
                try:
                    await context.bot.copy_message(
                        chat_id=uid,
                        from_chat_id=original.chat.id,
                        message_id=original.message_id
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
                        "user_id": uid,
                        "reason": reason,
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

    # 4) Kick off tasks and live progress updates
    total = len(user_ids)
    progress_msg = await query.edit_message_text(f"📤 Sending… 0/{total}")

    BATCH = 200  # update progress every ~200 users
    tasks = []
    for i, uid in enumerate(user_ids, 1):
        tasks.append(asyncio.create_task(send_one(uid)))
        if i % BATCH == 0:
            # allow some tasks to advance, then update progress
            await asyncio.sleep(0.1)
            sent = (
                counts["delivered"]
                + counts["delivered_after_retry"]
                + counts["skipped_suppressed"]
                + counts["blocked"]
                + counts["deleted_or_invalid"]
                + counts["network_error"]
                + counts["error"]
            )
            try:
                await progress_msg.edit_text(f"📤 Sending… {sent}/{total}")
            except Exception:
                pass

    await asyncio.gather(*tasks)

    # 5) Close log + apply suppression
    log_file.close()
    _append_suppression(new_suppressed_rows)

    # 6) Final summary
    summary = (
        "✅ Broadcast complete\n"
        f"• delivered: {counts['delivered']}\n"
        f"• delivered_after_retry: {counts['delivered_after_retry']}\n"
        f"• blocked: {counts['blocked']}\n"
        f"• deleted_or_invalid: {counts['deleted_or_invalid']}\n"
        f"• skipped_suppressed: {counts['skipped_suppressed']}\n"
        f"• network_error: {counts['network_error']}\n"
        f"• error: {counts['error']}\n\n"
        f"🧾 Log saved: {log_path}"
    )

    # add percentage lines for quick read
    def _pct(n, d):
        return f"{(n/d*100):.1f}%" if d else "0%"

    total_sent = (
        counts["delivered"]
        + counts["delivered_after_retry"]
        + counts["blocked"]
        + counts["deleted_or_invalid"]
        + counts["skipped_suppressed"]
        + counts["network_error"]
        + counts["error"]
    )

    percent_summary = (
        f"\n% delivered: {_pct(counts['delivered'], total_sent)}"
        f"\n% blocked: {_pct(counts['blocked'], total_sent)}"
        f"\n% deleted_or_invalid: {_pct(counts['deleted_or_invalid'], total_sent)}"
    )

    await progress_msg.edit_text(summary + percent_summary)



# Step 4: Cancel broadcast
async def cancel_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    await update.callback_query.edit_message_text("🚫 Broadcast cancelled.")

async def support(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = (
        "💬 *Contact Support*\n\n"
        "Please read before messaging\n\n"
        "*I personally handle only:*\n"
        "💳 Payment or billing issues\n"
        "🔐 Access problems to VIP channels\n"
        "🤝 Serious business or partnership inquiries\n\n"
        "*I do NOT reply to:*\n"
        "⛔ Win-rate or guarantees\n"
        "⛔ Scam accusations or low-effort messages\n"
        "⛔ System analysis or reverse-engineering\n\n"
        "For general questions\n"
        "use the help bot\n"
        "🤖 @MyPremiumHelpBot\n\n"
        "📩 Direct support\n"
        "👉 @The100xMooncaller"
    )

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("⬅️ Return to Menu", callback_data="go_home")]
    ])

    await update.callback_query.answer()

    await update.callback_query.edit_message_text(
        text=message,
        reply_markup=keyboard,
        parse_mode=constants.ParseMode.MARKDOWN,
        disable_web_page_preview=True
    )


async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = (
        "🚀 Solana100xCall | Premium Signals\n\n"
        "The real alpha. No fluff.\n\n"
        "💎 What's Inside:\n"
        "🥷 Sniper Signals (ultra-early entries)\n"
        "⚡ ALPHA Signals (best daily opportunities)\n"
        "💎 APEX Signals (peak confirmation)\n"
        "🏆 Milestone Tracker (live profit updates)\n"
        "💬 VIP Trader Chat\n\n"
        "📊 30+ quality signals daily\n"
        "🏆 100+ verified 10x-100x calls\n"
        "👥 300+ active traders\n\n"
        "🔥 FLASH SALE | 50% OFF LIFETIME ONLY\n"
        "👑 Lifetime: $49 (was $99)\n"
        "⏰ Ends in 72 hours\n\n"
        "🔥 1 Month: $44 (20% off)\n"
        "💎 3 Months: $63 (20% off)\n\n"
        "👇 Choose your plan"
    )

    keyboard = InlineKeyboardMarkup([
    [InlineKeyboardButton("🔥 View Memberships", callback_data="view_memberships")],
    [InlineKeyboardButton("💬 Member Testimonials", callback_data="show_testimonials")],
    [InlineKeyboardButton("📊 See Live Signals Preview", callback_data="show_signals_preview")],
    [InlineKeyboardButton("📲 Join FREE Main Channel", url="https://t.me/Solana100xcall")],
    [InlineKeyboardButton("🏆 100x+ Call Gallery", url="https://solana100xcall.fun/")],
    [
        InlineKeyboardButton("🤖 Help Bot", url="https://t.me/MyPremiumHelpBot"),
        InlineKeyboardButton("💬 Contact Support", callback_data="show_support")
    ]
])

    if update.callback_query:
        query = update.callback_query
        await query.answer()
        try:
            await query.edit_message_text(
                text=message, 
                reply_markup=keyboard,
                parse_mode=constants.ParseMode.MARKDOWN, 
                disable_web_page_preview=True
            )
            context.chat_data["menu_message_id"] = query.message.message_id
            context.chat_data["menu_chat_id"] = query.message.chat.id
        except Exception:
            menu_msg = await context.bot.send_message(
                chat_id=query.message.chat.id, 
                text=message, 
                reply_markup=keyboard,
                parse_mode=constants.ParseMode.MARKDOWN, 
                disable_web_page_preview=True
            )
            context.chat_data["menu_message_id"] = menu_msg.message_id
            context.chat_data["menu_chat_id"] = menu_msg.chat.id
    else:
        chat_id = update.effective_chat.id
        if update.message:
            try:
                await update.message.delete()
            except Exception:
                pass

        menu_id = context.chat_data.get("menu_message_id")
        menu_chat = context.chat_data.get("menu_chat_id", chat_id)
        if menu_id:
            try:
                await context.bot.edit_message_text(
                    chat_id=menu_chat, 
                    message_id=menu_id, 
                    text=message,
                    reply_markup=keyboard, 
                    parse_mode=constants.ParseMode.MARKDOWN,
                    disable_web_page_preview=True
                )
            except Exception:
                menu_msg = await context.bot.send_message(
                    chat_id=chat_id, 
                    text=message, 
                    reply_markup=keyboard,
                    parse_mode=constants.ParseMode.MARKDOWN, 
                    disable_web_page_preview=True
                )
                context.chat_data["menu_message_id"] = menu_msg.message_id
                context.chat_data["menu_chat_id"] = menu_msg.chat.id
        else:
            menu_msg = await context.bot.send_message(
                chat_id=chat_id, 
                text=message, 
                reply_markup=keyboard,
                parse_mode=constants.ParseMode.MARKDOWN, 
                disable_web_page_preview=True
            )
            context.chat_data["menu_message_id"] = menu_msg.message_id
            context.chat_data["menu_chat_id"] = menu_msg.chat.id

async def show_memberships(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
    "💎 <b>Membership Plans</b>\n\n"

    "🔥 FLASH SALE | 50% OFF LIFETIME ONLY\n"
    "👑 Lifetime: <b>$49</b> (was $99)\n"
    "⏰ Ends in 72 hours\n\n"

    "🔥 <b>1 MONTH</b> | <s>$55</s> → <b>$44</b>\n"
    "• Full access for 30 days\n"
    "• 300 elite wallets bonus\n\n"

    "💎 <b>3 MONTHS</b> | <s>$79</s> → <b>$63</b> ⭐ POPULAR\n"
    "• Full access for 90 days\n"
    "• 500 elite wallets bonus\n"
    "• Save 52% vs monthly\n\n"

    "👑 <b>LIFETIME</b> | <s>$99</s> → <b>$49</b> 🔥 FLASH SALE\n"
    "• One payment, lifetime access\n"
    "• 2,000 elite wallets bonus\n"
    "• All future updates included\n"
    "• 50% OFF ends in 72 hours\n\n"
    
    "🎯 <b>What You Get:</b>\n"
    "🥷 Sniper Signals (ultra-early entries)\n"
    "⚡ ALPHA Signals (best opportunities)\n"
    "💎 APEX Signals (peak confirmation)\n"
    "🏆 Milestone Tracker (live updates)\n"
    "💬 Active Trader Chat\n\n"
    
    "📊 30+ signals daily with instant buy buttons\n\n"
    
    "👇 Choose your plan"
)
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔥 1 Month | $44", callback_data="plan_1month")],
        [InlineKeyboardButton("💎 3 Months | $63 (POPULAR)", callback_data="plan_3month")],
        [InlineKeyboardButton("👑 Lifetime | $49 (FLASH SALE)", callback_data="plan_lifetime")],
        [InlineKeyboardButton("📊 Compare Plans", callback_data="compare_plans")],
        [InlineKeyboardButton("💰 ROI Calculator", callback_data="roi_calculator")],
        [InlineKeyboardButton("💳 Payment Info", callback_data="payment_info")],
        [InlineKeyboardButton("⬅️ Back to Menu", callback_data="go_home")]
    ])
    
    await update.callback_query.answer()
    await update.callback_query.edit_message_text(
        text=text,
        reply_markup=keyboard,
        parse_mode=constants.ParseMode.HTML,
        disable_web_page_preview=True
    )

async def show_testimonials(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "💬 *What Members Say*\n\n"
        
        "⭐⭐⭐⭐⭐ \"Hit 3 calls over 10x in 2 months\"\n"
        "\"Best signal service on Solana. The milestone tracker "
        "alone is worth it — I can see moves developing in real-time.\"\n"
        "— @AIAlphaKing (3-month member)\n\n"
        
        "⭐⭐⭐⭐⭐ \"Paid for itself in week 1\"\n"
        "\"Caught a Sniper signal that did 18x. My $79 lifetime "
        "membership paid for itself with ONE call. Insane value.\"\n"
        "— @Violet100xGem (Lifetime member)\n\n"
        
        "⭐⭐⭐⭐⭐ \"Finally, not exit liquidity\"\n"
        "\"Most signal groups are just pump and dumps. Here you're "
        "getting real alpha. Makes all the difference.\"\n"
        "— @IamDreamer920 (1-month member)\n\n"
        
        "⭐⭐⭐⭐⭐ \"30+ signals DAILY is insane\"\n"
        "\"Other groups send 5-10 signals per day. Here you get "
        "30+ QUALITY alerts. More opportunities = more wins.\"\n"
        "— @RooneyCryptoPolar (Lifetime member)\n\n"
        
        "📊 *The Numbers:*\n"
        "👥 300+ active members\n"
        "🏆 100+ verified 10x-100x calls\n"
        "⚡ 30+ signals daily\n\n"
        
        "👇 Join them today"
    )
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🚀 Get Lifetime | $49", url=MEMBERSHIP_LINK)],
        [InlineKeyboardButton("💎 View All Plans", callback_data="view_memberships")],
        [InlineKeyboardButton("⬅️ Back", callback_data="view_memberships")]  # ← CAMBIO
    ])
    
    await update.callback_query.answer()
    await update.callback_query.edit_message_text(
        text=text,
        reply_markup=keyboard,
        parse_mode=constants.ParseMode.MARKDOWN,
        disable_web_page_preview=True
    )
    
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "go_home":
        await show_main_menu(update, context)

    elif query.data == "view_memberships":
        await show_memberships(update, context)

    elif query.data == "plan_1month":
        await show_1month(update, context)

    elif query.data == "plan_3month":
        await show_3month(update, context)

    elif query.data == "plan_lifetime":
        await show_lifetime(update, context)

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

    elif query.data == "roi_calculator":
        await roi_calculator(update, context)


# -------- Main --------

# --- Admin utils: latest log + summary ---

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


def main():
    logging.basicConfig(level=logging.INFO)
    application = Application.builder().token(BOT_TOKEN).build()

    # ➕ Add standard command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("subscribe", subscribe_command))
    application.add_handler(CommandHandler("join", join_command))

    # 🧾 Admin utility commands
    application.add_handler(CommandHandler("lastlog", lastlog))
    application.add_handler(CommandHandler("broadcast_stats", broadcast_stats))

    # ✅ Broadcast system for admin
    application.add_handler(CommandHandler("broadcast", broadcast))  # Trigger
    # Admin reply for broadcast content — exclude /commands so admin utils still work
    application.add_handler(
        MessageHandler(
            filters.User(ADMIN_ID) & (filters.TEXT | filters.PHOTO) & ~filters.COMMAND,
            handle_broadcast
        )
    )
    application.add_handler(CallbackQueryHandler(confirm_broadcast, pattern="^confirm_broadcast$"))  # Confirm
    application.add_handler(CallbackQueryHandler(cancel_broadcast, pattern="^cancel_broadcast$"))    # Cancel

    # 📲 Inline button logic
    application.add_handler(CallbackQueryHandler(button_handler))

    logging.info("Bot is running...")
    application.run_polling()

    # ✅ Log storage paths after startup
    logging.info(f"[storage] BASE_DIR={BASE_DIR} LOGS_DIR={LOGS_DIR} BACKUPS_DIR={BACKUPS_DIR}")


if __name__ == "__main__":
    main()
