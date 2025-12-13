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
from telegram.error import Forbidden, BadRequest, RetryAfter, NetworkError

from sheets import log_user
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# Load environment variables
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
MEMBERSHIP_LINK = "https://t.me/onlysubsbot?start=bXeGHtzWUbduBASZemGJf"
ADMIN_ID = 7906225936
BANNER_URL = "https://ibb.co/KpDfxQY9"  # the working one



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
    try:
        await bot.send_photo(chat_id=chat_id, photo=BANNER_URL)
    except Exception as e:
        logging.warning(f"[banner] fallback to link message: {e}")
        await bot.send_message(chat_id=chat_id, text=f"🖼️ {BANNER_URL}")





# -------- Handlers --------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    try:
        log_user(user.id, user.first_name, user.username)
    except Exception as e:
        logging.warning(f"[Google Sheets] Failed to log user {user.id}: {e}")

    payload = context.args[0] if context.args else None
    logging.info(f"[START] User {user.id} (@{user.username}) joined with payload: {payload}")

    await context.bot.send_message(
        chat_id=ADMIN_ID,
        text=(
            f"{user.first_name}🎐 (@{user.username}) (#u{user.id}) has just launched this bot for the first time.\n\n"
            "You can send a private message to this member by replying to this message."
        )
    )

    # 🚩 send the banner exactly like the working bot (album URL is fine)
    await send_banner(context.bot, user.id)



    # --- hero message + plan buttons (sent once) ---
    message = (
        "🚀 Solana100xcall Premium Trading Signals\n\n"
        "Everything you need to trade Solana with precision.\n\n"
        "Membership Includes:\n"
        "✅ 3 VIP alert channels (Sniper Signals, Momentum Signals, Surge Signals)\n"
        "✅ VIP trader chatroom\n"
        "✅ VIP milestone-tracker channel\n"
        "✅ Help bot for quick answers\n\n"
        "Alerts:\n"
        "🟢 Automated smart-money signals 24/7\n"
        "🟢 Early detections on new launches\n"
        "🟢 Full token info (CA, LP, volume etc)\n"
        "🟢 Quick-buy buttons on major bots/Dexes\n"
        "🟢 High-quality, filtered alerts daily\n\n"
        "🎁 Bonuses:\n"
        "⭐️ 300 top Solana wallets (Monthly)\n"
        "🔥 500 top Solana wallets (3-Month)\n"
        "💎 1,000 top Solana wallets (Lifetime)\n"
        "Import-ready wallets compatible with Axiom, Padre, Gmgn and major Dexes"
    )

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("⚡ 1 Month VIP Alpha Access", callback_data="plan_1month")],
        [InlineKeyboardButton("🔥 3 Month VIP Alpha Access", callback_data="plan_3month")],
        [InlineKeyboardButton("👑 Lifetime VIP Alpha Access (20% OFF)", callback_data="plan_lifetime")],
        [InlineKeyboardButton("📲 Join FREE Main Channel", url="https://t.me/Solana100xcall")],
        [InlineKeyboardButton("🥇 Real Results (Phanes Verified)", url="https://t.me/Solana100xcallBoard")],
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
        "🧠 *How the Signals Work*\n\n"
        "⚙️ Our system scans thousands of elite Solana wallets 24/7\n"
        "📡 Detects early smart money entries, fresh launches, and momentum surges in real time\n\n"
        "Each alert includes:\n"
        "• 💰 Token with CA, LP, volume, holders\n"
        "• ⚡ One-tap buy via Trojan, Bloom, Gmgn bot\n"
        "• 🎯 Only verified trades, filtered for precision, zero noise\n\n"
        "🤖 Fully automated, always live, always early\n"
        "📈 Dozens of high quality signals daily\n\n"
        "💬 Need help? [@The100xMooncaller](https://t.me/The100xMooncaller)"
    )
    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Return to Menu", callback_data="go_home")]])

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
"   • Understanding how alerts work\n"
"   • How to import the wallet lists\n"
"   • Troubleshooting issues or errors\n\n"
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
        [InlineKeyboardButton("📲 Join Free Channel", url="https://t.me/Solana100xcall")],
        [InlineKeyboardButton("⬅️ Return to Menu", callback_data="go_home")]
    ])

    text = (
    "💳 *Subscribe to VIP Access*\n\n"
    "*Choose your plan:*\n"
    "💼 *1 Month VIP* — $49 USD\n"
    "🔥 *3 Month VIP* — $69.3 USD\n"
    "👑 *Lifetime VIP* — $71 USD *(20% OFF applied)*\n\n"
    "*What you unlock:*\n"
    "⚡ 3 VIP alert channels (Sniper Signals, Momentum Signals, Surge Signals)\n"
    "💬 VIP trader chat + milestone channel\n"
    "📘 Full trading framework to follow the signals\n\n"
    "🎁 *Wallet Bonuses:*\n"
    "⭐️ 300 top Solana wallets (Monthly)\n"
    "🔥 500 top Solana wallets (3-Month)\n"
    "💎 1,000 top Solana wallets (Lifetime)\n"
    "Import-ready wallets compatible with Axiom, Padre, Gmgn and major Dexes"
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



async def show_1month(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
    "⚡️ <b>1 Month VIP Access</b>\n"
"<b>$49 USD</b>\n\n"
"<b>Unlock:</b>\n"
"✅ VIP Sniper Signals Channel\n"
"✅ VIP Momentum Signals Channel\n"
"✅ VIP Surge Signals Channel\n"
"✅ VIP Trader Chatroom\n"
"✅ VIP Milestone-Tracker Channel\n"
"✅ Help Bot\n\n"
"🔹 Automated smart-money alerts 24/7\n"
"🔹 Early detections on new launches\n"
"🔹 Full token breakdown + instant buy links\n"
"🔹 High-quality, filtered signals only\n\n"
"🎁 <b>Bonus:</b> 300 top Solana smart-money wallets\n"
"(Import-ready) compatible with Axiom, Padre, Gmgn and major Dexes\n\n"
"💳 Tap below to activate your monthly access instantly"

)

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🪙 Pay With SOL/BNB/ETH Chain", url=MEMBERSHIP_LINK)],
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
    "🔥 <b>3 Month VIP Access</b>\n"
    "<b>$69.3 USD</b>\n\n"
    "Stronger commitment. Deeper time in VIP.\n\n"
    "<b>Unlock:</b>\n"
    "✅ VIP Sniper Signals Channel\n"
    "✅ VIP Momentum Signals Channel\n"
    "✅ VIP Surge Signals Channel\n"
    "✅ VIP Trader Chatroom\n"
    "✅ VIP Milestone-Tracker Channel\n"
    "✅ Help Bot\n\n"
    "🔹 Automated smart-money alerts 24/7\n"
    "🔹 Early detections on new launches\n"
    "🔹 Full token breakdown + instant buy links\n"
    "🔹 High-quality, filtered signals only\n\n"
    "🎁 <b>Bonus:</b> 500 top Solana smart-money wallets\n"
    "(import-ready) Works with Axiom, Padre, Gmgn and major Dexes\n\n"
    "💳 Tap below to activate your 3-month access instantly"
    )

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🪙 Pay with SOL, BNB or ETH", url=MEMBERSHIP_LINK)],
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
    "<s>$88.8 USD</s> <b>$71 USD</b> <b>(20% OFF)</b>\n\n"
    "One payment. Unlimited access forever.\n\n"
    "<b>Unlock:</b>\n"
    "✅ VIP Sniper Signals Channel\n"
    "✅ VIP Momentum Signals Channel\n"
    "✅ VIP Surge Signals Channel\n"
    "✅ VIP Trader Chatroom\n"
    "✅ VIP Milestone-Tracker Channel\n"
    "✅ Help Bot\n\n"
    "🔹 Automated smart-money alerts 24/7\n"
    "🔹 Early detections on new launches\n"
    "🔹 Full token breakdown + instant buy links\n"
    "🔹 High-quality, filtered signals only\n\n"
    "🎁 <b>Bonus:</b> 1,000 top Solana smart-money wallets\n"
    "(import-ready) Compatible with Axiom, Padre, Gmgn and major Dexes\n\n"
    "💳 Tap below to activate your lifetime access instantly"
)


    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🪙 Pay With SOL/BNB/ETH Chain", url=MEMBERSHIP_LINK)],
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
        [InlineKeyboardButton("📲 Join Free Channel", url="https://t.me/Solana100xcall")],
        [InlineKeyboardButton("⬅️ Return to Menu", callback_data="go_home")]
    ])

    text = (
    "💳 *Subscribe to VIP Access*\n\n"
    "*Plans available:*\n"
    "💼 *1 Month VIP* — $49 USD\n"
    "👑 *Lifetime VIP* — $71 USD *(20% OFF applied)*\n\n"
    "*What you unlock instantly:*\n"
    "📡 3 VIP alert channels (Sniper, Momentum, Surge)\n"
    "💬 VIP trader chatroom\n"
    "📈 Milestone-tracker + full trading framework\n\n"
    "🎁 *Wallet Bonuses:*\n"
    "⭐ 300 top Solana wallets for 1-Month members\n"
    "💎 1,000 top Solana wallets for Lifetime members\n"
    "(Import-ready for BullX, Axiom, Padre, GMGN)\n\n"
    "Payments are handled securely in the membership bot using SOL, BNB, or ETH.\n"
    "Tap *Get VIP Signals* to open it, or check the *Free Channel* first if you prefer."
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
"Before you message me, please read this carefully:\n\n"
"I personally handle:\n"
"💳 Payment or billing issues\n"
"🔐 Problems accessing your VIP channels or bonuses\n"
"🤝 Serious collaboration or partnership inquiries\n\n"
"I do *not* reply to:\n"
"⛔ Win rate, backtests, or performance-proof requests\n"
"⛔ “Is this a scam?” or similar low-effort questions\n"
"⛔ Attempts to analyze or reverse-engineer the system\n\n"
"For all general questions about how the bot works, how alerts function, or how to use the wallet lists, please message the help bot: @MyPremiumHelpBot\n\n"
"If your question matches the allowed topics above, you can contact me directly here:\n"
"📩 [@The100xMooncaller](https://t.me/The100xMooncaller)"

    )

    keyboard = InlineKeyboardMarkup(
        [[InlineKeyboardButton("⬅️ Return to Menu", callback_data="go_home")]]
    )

    await update.callback_query.edit_message_text(
        text=message,
        reply_markup=keyboard,
        parse_mode=constants.ParseMode.MARKDOWN,
        disable_web_page_preview=True
    )
async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = (
        "🚀 Solana100xcall Premium Trading Signals\n\n"
"Everything you need to trade Solana with precision.\n\n"
"Membership Includes:\n"
"✅ 3 VIP alert channels (Sniper Signals, Momentum Signals, Surge Signals)\n"
"✅ VIP trader chatroom\n"
"✅ VIP milestone-tracker channel\n"
"✅ Help bot for quick answers\n\n"
"Alerts:\n"
"🟢 Automated smart-money signals 24/7\n"
"🟢 Early detections on new launches\n"
"🟢 Full token info (CA, LP, volume etc)\n"
"🟢 Quick-buy buttons on major bots/Dexes\n"
"🟢 High-quality, filtered alerts daily\n\n"
"🎁 Bonuses:\n"
"⭐️ 300 top Solana wallets (Monthly)\n"
"🔥 500 top Solana wallets (3-Month)\n"
"💎 1,000 top Solana wallets (Lifetime)\n"
"Import-ready wallets compatible with Axiom, Padre, Gmgn and major Dexes"
    )


    keyboard = InlineKeyboardMarkup([
    [InlineKeyboardButton("⚡ Unlock 1 Month Access", callback_data="plan_1month")],
    [InlineKeyboardButton("🔥 Unlock 3 Month Access", callback_data="plan_3month")],
    [InlineKeyboardButton("👑 Unlock Lifetime Access (20% OFF)", callback_data="plan_lifetime")],
    [InlineKeyboardButton("📲 Join FREE Main Channel", url="https://t.me/Solana100xcall")],
    [InlineKeyboardButton("🥇 Real Results (Phanes Verified)", url="https://t.me/Solana100xcallBoard")],
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
                text=message, reply_markup=keyboard,
                parse_mode=constants.ParseMode.MARKDOWN, disable_web_page_preview=True
            )
            context.chat_data["menu_message_id"] = query.message.message_id
            context.chat_data["menu_chat_id"] = query.message.chat.id
        except Exception:
            menu_msg = await context.bot.send_message(
                chat_id=query.message.chat.id, text=message, reply_markup=keyboard,
                parse_mode=constants.ParseMode.MARKDOWN, disable_web_page_preview=True
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
                    chat_id=menu_chat, message_id=menu_id, text=message,
                    reply_markup=keyboard, parse_mode=constants.ParseMode.MARKDOWN,
                    disable_web_page_preview=True
                )
            except Exception:
                menu_msg = await context.bot.send_message(
                    chat_id=chat_id, text=message, reply_markup=keyboard,
                    parse_mode=constants.ParseMode.MARKDOWN, disable_web_page_preview=True
                )
                context.chat_data["menu_message_id"] = menu_msg.message_id
                context.chat_data["menu_chat_id"] = menu_msg.chat.id
        else:
            menu_msg = await context.bot.send_message(
                chat_id=chat_id, text=message, reply_markup=keyboard,
                parse_mode=constants.ParseMode.MARKDOWN, disable_web_page_preview=True
            )
            context.chat_data["menu_message_id"] = menu_msg.message_id
            context.chat_data["menu_chat_id"] = menu_msg.chat.id
    
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "show_howsignals":
        await show_howsignals(update, context)
    elif query.data == "show_support":
        await support(update, context)
    elif query.data == "go_home":
        await show_main_menu(update, context)
    elif query.data == "plan_1month":
        await show_1month(update, context)
    elif query.data == "plan_lifetime":
        await show_lifetime(update, context)

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
