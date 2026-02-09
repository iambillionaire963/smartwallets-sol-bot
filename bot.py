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

    await send_banner(context.bot, user.id)

    message = (
    "🚀 Solana100xCall VIP | Real-Time Alpha\n\n"
    "We monitor 10,000+ smart money wallets 24/7.\n"
    "Detect elite moves before the crowd.\n\n"
    "🏆 PROVEN TRACK RECORD:\n"
    "✅ 100+ verified 10x-100x calls\n"
    "✅ View gallery: solana100xcall.fun\n\n"
    "🎯 WHAT YOU GET:\n"
    "🥷 VIP Sniper Signals (early entries)\n"
    "⚡ VIP Momentum Signals (trend follow)\n"
    "🌊 VIP Surge Signals (volume & traction)\n"
    "🏆 VIP Milestone Tracker (live X updates)\n"
    "💬 VIP Trader Chat (active community)\n\n"
    "📊 30-50 quality signals daily\n"
    "⚡ Instant buy buttons (Trojan, Bloom, Maestro)\n"
    "🔗 Instant buttons to Dexes (Axiom, Padre, Trojan Web)\n"
    "🔔 Zero noise, only verified smart money\n\n"
    "💰 SPECIAL OFFER | 20% OFF:\n"
    "🔥 1 Month: $44 (was $55)\n"
    "💎 3 Months: $63 (was $79) | BEST VALUE\n"
    "👑 Lifetime: $79 (was $99) | LIMITED SPOTS\n\n"
    "👇 Choose your plan now"
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
        "🧠 *How Our System Works*\n\n"
        "🔍 *THE EDGE:*\n"
        "We monitor 10,000+ elite Solana wallets 24/7\n"
        "When smart money moves, you know instantly\n\n"
        "⚙️ *THE PROCESS:*\n\n"
        "*Step 1: Detection*\n"
        "→ Elite wallets start buying token ABC\n"
        "→ System detects clustering pattern\n"
        "→ Smart money signal identified\n\n"
        "*Step 2: Alert Tiers*\n"
        "🥷 SNIPER: Early entries detected\n"
        "⚡ MOMENTUM: Trend forming\n"
        "🌊 SURGE: Major move incoming\n\n"
        "*Step 3: You Get Alert*\n"
        "→ Token address (CA)\n"
        "→ Current price & market cap\n"
        "→ Liquidity & holder count\n"
        "→ Instant buy buttons (Trojan, Bloom, Maestro)\n"
        "→ Chart links (DexScreener, Axiom, Padre)\n\n"
        "*Step 4: Milestone Tracking*\n"
        "→ We track every signal 24/7\n"
        "→ When it hits 2x, 3x, 5x, 10x+ → you get update\n"
        "→ Never miss profit-taking opportunities\n\n"
        "📊 *THE NUMBERS:*\n"
        "• 10,000+ wallets monitored\n"
        "• 30-50 signals per day\n"
        "• 100+ verified 10x-100x calls\n"
        "• Response time: <30 seconds\n\n"
        "🎯 *WHY IT WORKS:*\n"
        "Most traders react to price charts\n"
        "We see the wallets BEFORE charts move\n"
        "By the time retail sees pump, we're in\n\n"
        "🏆 *Proven Results:*\n"
        "View our 100x+ gallery: solana100xcall.fun\n\n"
        "👇 Ready to get the edge?"
    )
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🚀 Get VIP Access Now", callback_data="view_memberships")],
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
    "🆘 *Help & How This Bot Works*\n\n"
"This bot is your gateway to the Solana100xcall VIP system.\n\n"
"*What this bot does:*\n"
"🔹 Shows all VIP plans, prices, and bonuses\n"
"🔹 Redirects you to the membership bot to complete your payment\n"
"🔹 Automatically unlocks your VIP channels once your membership is active\n\n"
"*How alerts work (quick overview):*\n"
"⚡ Tracks elite Solana wallets 24/7\n"
"📡 Detects launches, momentum spikes, smart-money entries, and liquidity shifts\n"
"📲 Each alert includes CA, LP, volume, holders, price data, and instant buy links\n\n"
"*Where to ask questions:*\n"
"🤖 Use *@MyPremiumHelpBot* for:\n"
"   🔹 Understanding how alerts work\n"
"   🔹 How to import the wallet lists\n"
"   🔹 Troubleshooting issues or errors\n\n"
"💳 For payment or access problems only, tap *Contact Support* in the main menu.\n"

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
        [InlineKeyboardButton("🚀 Get VIP Signals", url=MEMBERSHIP_LINK)],
            [InlineKeyboardButton("🏆 100x+ Call Gallery", url="https://solana100xcall.fun/")],
        [InlineKeyboardButton("📲 Join Free Channel", url="https://t.me/Solana100xcall")],
        [InlineKeyboardButton("⬅️ Return to Menu", callback_data="go_home")]
    ])

    text = (
    "💳 *Subscribe to VIP Access*\n\n"
    "Choose your membership:\n"
    "🔥 1 Month VIP\n"
    "💎 3 Month VIP\n"
    "👑 Lifetime VIP\n\n"
    "*VIP Access includes:*\n"
    "🥷 VIP Sniper Signals (early entries)\n"
    "⚡ VIP Momentum Signals (trend follow)\n"
    "🌊 Surge Signals (volume & traction)\n"
    "🏆 Milestone Signals (3x · 6x · 9x+ moves)\n"
    "💬 Active VIP trader chatroom\n\n"
    "🎁 *Wallet Bonuses:*\n"
    "🔥 300 top Solana wallets (1 Month)\n"
    "💎 500 top Solana wallets (3 Months)\n"
    "👑 1,000 top Solana wallets (Lifetime)\n\n"
    "🧩 Import-ready wallets\n"
    "(Axiom · Padre · GMGN · major Solana Dexes)\n\n"
    "⚡ Access is activated automatically after you made the payment"
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
        
        "This is what you'll receive in VIP:\n\n"
        
        "🥷 *SNIPER SIGNAL EXAMPLE:*\n"
        "```\n"
        "🥷 SNIPER ALERT\n"
        "Elite wallets buying NOW\n\n"
        "$PEPE2 | 0x1a2b3c...\n"
        "MC: $45K → $180K (4x in 15 min)\n"
        "LP: $12K | Holders: 89\n"
        "Volume: $45K (24h)\n\n"
        "[Buy on Trojan] [Buy on Bloom]\n"
        "[DexScreener] [Axiom]\n"
        "```\n\n"
        
        "⚡ *MOMENTUM SIGNAL EXAMPLE:*\n"
        "```\n"
        "⚡ MOMENTUM ALERT\n"
        "Smart money accumulating\n\n"
        "$DOGE2 | 0x4d5e6f...\n"
        "MC: $890K → $2.4M (2.7x)\n"
        "LP: $67K | Holders: 234\n"
        "Volume: $890K (24h)\n\n"
        "[Buy on Trojan] [Buy on Maestro]\n"
        "[DexScreener] [Padre]\n"
        "```\n\n"
        
        "🏆 *MILESTONE UPDATE EXAMPLE:*\n"
        "```\n"
        "🏆 MILESTONE REACHED\n"
        "$WIF hit 12x from our call!\n\n"
        "Entry MC: $250K\n"
        "Current MC: $3.1M\n"
        "Your $100 → $1,200 💰\n\n"
        "[View Chart]\n"
        "```\n\n"
        
        "⚡ You'll get 30-50 signals like these DAILY\n"
        "🎯 All with instant buy buttons\n"
        "📊 Real-time updates via Milestone Tracker\n\n"
        
        "👇 Get full access now"
    )
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🚀 Subscribe Now", callback_data="view_memberships")],
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
        "📊 *Compare VIP Plans*\n\n"
        
        "```\n"
        "Feature          | 1M | 3M | LT\n"
        "─────────────────┼────┼────┼────\n"
        "Sniper Signals   | ✅ | ✅ | ✅\n"
        "Momentum Signals | ✅ | ✅ | ✅\n"
        "Surge Signals    | ✅ | ✅ | ✅\n"
        "Milestone Track  | ✅ | ✅ | ✅\n"
        "VIP Chat         | ✅ | ✅ | ✅\n"
        "Buy Bot Buttons  | ✅ | ✅ | ✅\n"
        "Elite Wallets    |300 |500 | 1K\n"
        "Future Updates   | ❌ | ❌ | ✅\n"
        "Never Pay Again  | ❌ | ❌ | ✅\n"
        "```\n\n"
        
        "💰 *Cost Per Month:*\n"
        "• 1 Month: $44/month\n"
        "• 3 Months: $21/month (save 52%)\n"
        "• Lifetime: $0/month after first payment\n\n"
        
        "🎯 *Best For:*\n"
        "• 1 Month: Testing the system\n"
        "• 3 Months: Serious traders (most popular)\n"
        "• Lifetime: Long-term investors (best value)\n\n"
        
        "💡 *Quick Math:*\n"
        "If you stay for 3+ months:\n"
        "→ Monthly plan = $132+\n"
        "→ Lifetime plan = $79 total\n"
        "→ You save $53+ immediately\n\n"
        
        "🏆 *Recommendation:*\n"
        "If you're serious about Solana memecoins,\n"
        "get Lifetime. It pays for itself in 2 months.\n\n"
        
        "👇 Choose your plan"
    )
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔥 1 Month | $44", callback_data="plan_1month")],
        [InlineKeyboardButton("💎 3 Months | $63 (POPULAR)", callback_data="plan_3month")],
        [InlineKeyboardButton("👑 Lifetime | $79 (BEST VALUE)", callback_data="plan_lifetime")],
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
        "🔒 *Payment & Security Information*\n\n"
        
        "💳 *Accepted Payment Methods:*\n"
        "✅ Solana (SOL)\n"
        "✅ Ethereum (ETH)\n"
        "✅ Binance Coin (BNB)\n\n"
        
        "⚡ *How Payment Works:*\n"
        "1. Click 'Subscribe Now' on any plan\n"
        "2. Opens secure OnlySubs payment bot\n"
        "3. Choose your payment method\n"
        "4. Complete payment\n"
        "5. Instant access (30-60 seconds)\n\n"
        
        "🔐 *Privacy & Security:*\n"
        "✅ No KYC required\n"
        "✅ Anonymous payments accepted\n"
        "✅ Telegram-based (private by default)\n"
        "✅ Your data is never shared\n"
        "✅ Secure payment processor (OnlySubs)\n\n"
        
        "⚡ *Instant Activation:*\n"
        "After payment, you'll receive:\n"
        "1. Invite link to VIP Sniper channel\n"
        "2. Invite link to VIP Momentum channel\n"
        "3. Invite link to VIP Surge channel\n"
        "4. Invite link to VIP Milestone channel\n"
        "5. Invite link to VIP Chat\n"
        "6. Download link for elite wallets bonus\n\n"
        
        "💬 *Support:*\n"
        "Payment issues? @The100xMooncaller\n"
        "General help? @MyPremiumHelpBot\n\n"
        
        "👇 Ready to join?"
    )
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🚀 Subscribe Now", callback_data="view_memberships")],
        [InlineKeyboardButton("📲 Visit Free Channel First", url="https://t.me/Solana100xcall")],
        [InlineKeyboardButton("⬅️ Back", callback_data="go_home")]
    ])
    
    await update.callback_query.edit_message_text(
        text=text,
        reply_markup=keyboard,
        parse_mode=constants.ParseMode.MARKDOWN,
        disable_web_page_preview=True
    )

async def roi_calculator(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "💰 *VIP Membership ROI Calculator*\n\n"
        
        "Let's see what you need to make profit:\n\n"
        
        "📊 *SCENARIO 1: Conservative*\n"
        "Membership: $79 (Lifetime)\n"
        "Your typical trade: $100\n"
        "You need: ONE 1x to break even\n"
        "→ If you catch 1 token that doubles\n"
        "→ You profit: $100 (covers membership + $21 profit)\n\n"
        
        "📊 *SCENARIO 2: Realistic*\n"
        "Membership: $79 (Lifetime)\n"
        "Your typical trade: $500\n"
        "You need: ONE 20% gain to break even\n"
        "→ Catch any token that does 1.2x\n"
        "→ You profit: $100 (covers membership + $21 profit)\n\n"
        
        "📊 *SCENARIO 3: Our Track Record*\n"
        "We've had 100+ calls hit 10x+\n"
        "If you catch just ONE with $200:\n"
        "→ Your $200 becomes $2,000\n"
        "→ Profit: $1,800\n"
        "→ ROI on membership: 2,178%\n\n"
        
        "🎯 *Bottom Line:*\n"
        "You need to catch ONE decent move\n"
        "to pay for your membership forever.\n\n"
        
        "📈 *Daily Opportunities:*\n"
        "• 30-50 signals per day\n"
        "• 900-1,500 signals per month\n"
        "• You only need 1-2 wins\n\n"
        
        "💡 *The Math is Simple:*\n"
        "Risk: $79 one time\n"
        "Upside: Unlimited winning opportunities\n"
        "Time to ROI: Usually first week\n\n"
        
        "👇 Start your ROI today"
    )
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🚀 Get Lifetime Access | $79", callback_data="plan_lifetime")],
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
        "🔥 <b>1 Month VIP Access</b>\n"
        "<s>$55</s> → <b>$44</b> (20% OFF)\n\n"
        "Full access to the Solana100xCall VIP system.\n\n"
        "<b>🚀 VIP Access includes:</b>\n"
        "🥷 VIP Sniper Signals (early entries)\n"
        "⚡ VIP Momentum Signals (trend follow)\n"
        "🏆 VIP Milestone Tracker (3×, 6×, 9×+ moves)\n"
        "🚀 Surge Signals (Volume & Traction)\n"
        "💬 VIP Active Trader Chatroom\n\n"
        "🔔 Signals are live, fast, and execution-focused.\n"
        "📊 Each signal includes CA, LP, volume & instant buy buttons to major trading bots.\n\n"
        "🎁 <b>Bonus:</b> 300 top Solana wallets\n"
        "(import-ready) to Axiom · Padre · GMGN \n\n"
        "💳 Tap below to activate your 1-month access"
    )


    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🪙 Pay with SOL / BNB / ETH", url=MEMBERSHIP_LINK)],
        [InlineKeyboardButton("⬅️ Return to Menu", callback_data="go_home")]
    ])

    await update.callback_query.edit_message_text(
        text=text,
        reply_markup=keyboard,
        parse_mode=constants.ParseMode.HTML,
        disable_web_page_preview=True
    )


async def show_3month(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "💎 <b>3 Month VIP Access</b>\n"
        "<s>$79</s> → <b>$63</b> (20% OFF)\n\n"
        "Extended access to the Solana100xCall VIP system.\n\n"
        "<b>🚀 VIP Access includes:</b>\n"
        "🥷 VIP Sniper Signals (early entries)\n"
        "⚡ VIP Momentum Signals (trend follow)\n"
        "🏆 VIP Milestone Tracker (3×, 6×, 9×+ moves)\n"
        "🚀 Surge Signals (Volume & Traction)\n"
        "💬 VIP Active Trader Chatroom\n\n"
        "🔔 Signals are live, fast, and execution-focused.\n"
        "📊 Each signal includes CA, LP, volume & instant buy buttons to major trading bots.\n\n"
        "🎁 <b>Bonus:</b> 500 top Solana wallets\n"
        "(import-ready) to Axiom · Padre · GMGN \n\n"
        "💳 Tap below to activate your 3-month access"
    )


    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🪙 Pay with SOL / BNB / ETH", url=MEMBERSHIP_LINK)],
        [InlineKeyboardButton("⬅️ Return to Menu", callback_data="go_home")]
    ])

    await update.callback_query.edit_message_text(
        text=text,
        reply_markup=keyboard,
        parse_mode=constants.ParseMode.HTML,
        disable_web_page_preview=True
    )

async def show_lifetime(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "👑 <b>Lifetime VIP Access</b>\n"
        "<s>$99</s> → <b>$79</b> (20% OFF)\n\n"
        "One payment. Permanent access to the Solana100xCall VIP system.\n\n"
        "<b>🚀 VIP Access includes:</b>\n"
        "🥷 VIP Sniper Signals (early entries)\n"
        "⚡ VIP Momentum Signals (trend follow)\n"
        "🏆 VIP Milestone Tracker (3×, 6×, 9×+ moves)\n"
        "🚀 Surge Signals (Volume & Traction)\n"
        "💬 VIP Active Trader Chatroom\n\n"
        "🔔 Signals are live, fast, and execution-focused.\n"
        "📊 Each signal includes CA, LP, volume & instant buy buttons to major trading bots.\n\n"
        "🎁 <b>Bonus:</b> 1,000 top Solana wallets\n"
        "(import-ready) to Axiom · Padre · GMGN \n\n"
        "♾️ No renewals. No limits.\n"
        "💳 Tap below to activate lifetime access"
    )

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🪙 Pay with SOL / BNB / ETH", url=MEMBERSHIP_LINK)],
        [InlineKeyboardButton("⬅️ Return to Menu", callback_data="go_home")]
    ])

    await update.callback_query.edit_message_text(
        text=text,
        reply_markup=keyboard,
        parse_mode=constants.ParseMode.HTML,
        disable_web_page_preview=True
    )

    

async def join_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🚀 Get VIP Signals", url=MEMBERSHIP_LINK)],
            [InlineKeyboardButton("🏆 100x+ Call Gallery", url="https://solana100xcall.fun/")],
        [InlineKeyboardButton("📲 Join Free Channel", url="https://t.me/Solana100xcall")],
        [InlineKeyboardButton("⬅️ Return to Menu", callback_data="go_home")]
    ])

    text = (
    "💳 *Get VIP Access*\n\n"
    "Choose your membership:\n"
    "🔥 1 Month VIP\n"
    "💎 3 Month VIP\n"
    "👑 Lifetime VIP\n\n"
    "*All memberships include:*\n"
    "🥷 VIP Sniper Signals (early entries)\n"
    "⚡ VIP Momentum Signals (trend follow)\n"
    "🏆 VIP Milestone Tracker (3×, 6×, 9×+ moves)\n"
    "🚀 Surge Signals (Volume & Traction)\n"
    "💬 VIP Active Trader Chatroom\n\n"
    "🟢 Real Solana memecoin signals\n"
    "🟢 Early entries with full token info\n"
    "🟢 Instant buy buttons on major bots\n\n"
    "⚡ Access is activated automatically after payment"
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
        "🚀 Solana100xCall VIP Memecoin Signals\n\n"
        "Private VIP system for serious Solana traders.\n\n"
        "🔓 What you get inside:\n"
        "🥷 VIP Sniper Signals (early entries)\n"
        "⚡ VIP Momentum Signals (trend follow)\n"
        "🌊 VIP Surge Signals (volume & traction)\n"
        "🏆 VIP Milestone Signals (3x · 6x · 9x+ moves)\n"
        "💬 Active VIP trader chatroom\n\n"
        "🔔 Signals are live, fast, and action-based\n"
        "📡 Running 24/7 on Solana\n"
        "👥 Hundreds of real traders inside\n\n"
        "This is NOT a public signals channel.\n"
        "This is where real traders operate.\n\n"
        "👇 Tap below to view VIP memberships"
    )

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔥 View Memberships", callback_data="view_memberships")],
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
        "💎 *VIP Membership Plans*\n\n"
        
        "🔥 *1 MONTH VIP* | ~~$55~~ → *$44*\n"
        "• Full VIP access for 30 days\n"
        "• 300 elite wallets bonus\n"
        "• Perfect for testing the system\n\n"
        
        "💎 *3 MONTHS VIP* | ~~$79~~ → *$63* ⭐ POPULAR\n"
        "• Full VIP access for 90 days\n"
        "• 500 elite wallets bonus\n"
        "• Best value for serious traders\n"
        "• Save 52% vs monthly plan\n\n"
        
        "👑 *LIFETIME VIP* | ~~$99~~ → *$79* 🏆 BEST VALUE\n"
        "• Permanent VIP access\n"
        "• 1,000 elite wallets bonus\n"
        "• Never pay again\n"
        "• All future updates included\n\n"
        
        "🎯 *All Plans Include:*\n"
        "🥷 VIP Sniper Signals (early entries)\n"
        "⚡ VIP Momentum Signals (trend follow)\n"
        "🌊 VIP Surge Signals (volume spikes)\n"
        "🏆 VIP Milestone Tracker (3x, 6x, 9x+)\n"
        "💬 VIP Active Trader Chat\n\n"
        
        "📊 30-50 quality signals daily\n"
        "⚡ Instant buy buttons (Trojan, Bloom, Maestro)\n"
        "🔔 24/7 smart money monitoring\n\n"
        
        "👇 Choose your plan or explore more"
    )
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔥 1 Month | $44", callback_data="plan_1month")],
        [InlineKeyboardButton("💎 3 Months | $63 (POPULAR)", callback_data="plan_3month")],
        [InlineKeyboardButton("👑 Lifetime | $79 (BEST VALUE)", callback_data="plan_lifetime")],
        [InlineKeyboardButton("📊 Compare Plans", callback_data="compare_plans")],
        [InlineKeyboardButton("💰 ROI Calculator", callback_data="roi_calculator")],
        [InlineKeyboardButton("💳 Payment Info", callback_data="payment_info")],
        [InlineKeyboardButton("⬅️ Back to Menu", callback_data="go_home")]
    ])
    
    await update.callback_query.answer()
    await update.callback_query.edit_message_text(
        text=text,
        reply_markup=keyboard,
        parse_mode=constants.ParseMode.MARKDOWN,
        disable_web_page_preview=True
    )

async def show_testimonials(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "💬 *What VIP Members Say*\n\n"
        
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
        "actually following REAL smart money. Makes all the difference.\"\n"
        "— @IamDreamer920 (1-month member)\n\n"
        
        "⭐⭐⭐⭐⭐ \"30-50 signals DAILY is insane\"\n"
        "\"Other groups send 5-10 signals per day. Here you get "
        "30-50 QUALITY alerts. More opportunities = more wins.\"\n"
        "— @RooneyCryptoPolar (Lifetime member)\n\n"
        
        "📊 *By The Numbers:*\n"
        "👥 300+ active VIP members\n"
        "🏆 100+ verified 10x-100x calls\n"
        "⚡ 30-50 signals daily\n"
        "🎯 10,000+ wallets monitored 24/7\n\n"
        
        "👇 Join them today"
    )
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔥 Get VIP Access Now", callback_data="view_memberships")],
        [InlineKeyboardButton("⬅️ Back to Menu", callback_data="go_home")]
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
