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
BANNER_URL = "https://imgur.com/a/cltw5k3"  # Confirmed correct

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

    # --- Move main menu message here ---
    message = (
"🚀 *Solana100xcall — Premium Trading Signals* 🚀\n\n"
"🚀 Trade smarter! Our AI scans 25,000+ tokens daily from LetsBonk, Pumpfun, Moonshot & top launchpads. 🤖 You get 30+ sniper-grade signals every day with instant buy options, 24/7.\n\n"
"🎁 *Bonus for all plans:* 100 Top Killer Smart Money Wallets ready to import\n"
"📦 Fully compatible with *BullX, Axiom, Padre, Gmgn* and all major DEX tools\n\n"
"👇 Choose a plan to upgrade your trading edge"
)
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("⚡ 1 Month VIP Access: 0.2 SOL • 20% OFF", callback_data="plan_1month")],
        [InlineKeyboardButton("👑 Lifetime VIP Access: 0.355 SOL • 20% OFF", callback_data="plan_lifetime")],
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
    "🧠 *How Signals Work*\n\n"
    "Our proprietary AI system continuously monitors thousands of elite Solana wallets with a combined PnL exceeding $1B.\n\n"
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
    await update.callback_query.edit_message_text(
        text=message,
        reply_markup=keyboard,
        parse_mode=constants.ParseMode.MARKDOWN,
        disable_web_page_preview=True
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = (
        "🆘 *Need Help?*\n\n"
        "This bot delivers sniper-grade Solana memecoin signals based on:\n"
        "• On-chain wallet tracking (thousands of smart wallets)\n"
        "• High-liquidity inflow detection\n"
        "• AI-powered trade pattern analysis\n\n"
        "You’ll receive:\n"
        "✅ Instant alerts with token data & copy-ready CAs\n"
        "✅ *Membership bonuses:* smart wallets for BullX, Axiom, Padre, Gmgn\n\n"
        "📬 For support, message [@The100xMooncaller](https://t.me/The100xMooncaller)"
    )

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("⬅️ Return to Menu", callback_data="go_home")]
    ])

    # Button click → edit that message
    if update.callback_query:
        await update.callback_query.answer()
        try:
            await update.callback_query.edit_message_text(
                text=message,
                reply_markup=keyboard,
                parse_mode=constants.ParseMode.MARKDOWN,
                disable_web_page_preview=True
            )
            context.chat_data["menu_message_id"] = update.callback_query.message.message_id
            context.chat_data["menu_chat_id"] = update.callback_query.message.chat.id
        except Exception:
            # fallback: send new and store id
            menu_msg = await context.bot.send_message(
                chat_id=update.callback_query.message.chat.id,
                text=message,
                reply_markup=keyboard,
                parse_mode=constants.ParseMode.MARKDOWN,
                disable_web_page_preview=True
            )
            context.chat_data["menu_message_id"] = menu_msg.message_id
            context.chat_data["menu_chat_id"] = menu_msg.chat.id

    else:
        # Typed command → delete it and edit the stored menu message (or send new one)
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

async def subscribe_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🚀 Get VIP Signals", url=MEMBERSHIP_LINK)],
        [InlineKeyboardButton("📲 Join Free Channel", url="https://t.me/Solana100xcall")],
        [InlineKeyboardButton("⬅️ Return to Menu", callback_data="go_home")]
    ])

    text = (
        "🚀 *Unlock Full VIP Access — Premium Signals*\n\n"
        "Gain instant alerts powered by AI & smart wallet tracking.\n\n"
        "📈 *What you get:*\n"
        "• 30+ sniper alerts daily for fresh Solana memecoins\n"
        "• Auto contract address detection & real-time metrics\n"
        "• Insights from 100+ elite wallets\n\n"
        "🎯 *First-mover advantage starts here — catch pumps before the hype!*"
    )

    # Button press → edit
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
        # Typed /subscribe → delete the user command, then edit stored menu
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
    "⚡ <b>1 Month Premium</b>\n"
    "<s>0.25 SOL</s> ➜ <b>0.2 SOL</b>  <i>(20% OFF)</i>\n\n"
    "📈 30+ sniper alerts/day for fresh Solana memecoins\n"
    "🤖 AI scans thousands of smart wallets with $1B+ PnL\n"
    "📲 Instant CA, LP, volume, chart — no delay, no fluff\n\n"
    "🎁 <b>Bonus:</b> 100 Top Killer Smart Money Wallets (import-ready)\n"
    "🧠 Works with <b>BullX, Axiom, Padre, Gmgn</b>\n\n"
    "💳 Tap below to unlock your access:"
)

    keyboard = InlineKeyboardMarkup([
    [InlineKeyboardButton("🪙 Pay 0.2 SOL", url=MEMBERSHIP_LINK)],
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
        "👑 <b>Lifetime Premium</b>\n"
        "<s>0.444 SOL</s> ➜ <b>0.355 SOL</b>  <i>(20% OFF)</i>\n\n"
        "📈 Unlimited access to AI-powered sniper signals\n"
        "🤖 Tracks thousands of elite wallets in real time\n"
        "📲 Auto CA, LP, volume, dev sold ⚡ 100% filtered\n\n"
        "🎁 <b>Bonus:</b> 100 Top Killer Smart Money Wallets (import-ready)\n"
        "🧠 For <b>BullX, Axiom, Padre, Gmgn</b> and advanced wallet tools\n\n"
        "💳 Tap below to unlock Lifetime access:"
    )

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🪙 Pay 0.355 SOL", url=MEMBERSHIP_LINK)],
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
        "🚀 *Join the Premium Signal Group*\n\n"
        "Gain exclusive AI-powered memecoin alerts based on real-time smart wallet tracking.\n\n"
        "📈 *Benefits of joining:*\n"
        "• 30+ premium memecoin alerts daily\n"
        "• Auto contract address (CA) detection & on-chain metrics\n"
        "• Insights from 100+ top-performing wallets\n\n"
        "🎯 *Stay ahead of the market — catch pumps before the hype!*"
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
        # Typed /join → delete the user command, then edit stored menu
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
    user_ids = get_all_user_ids()
    _backup_users_csv_json(user_ids)

    # 2) Load suppression
    suppressed = _load_suppressed_ids()

    # 3) Prepare log file and counters
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

    # 4) Send loop with logging
    for uid in user_ids:
        ts = datetime.datetime.now().isoformat(timespec="seconds")

        if uid in suppressed:
            counts["skipped_suppressed"] += 1
            log_writer.writerow({"user_id": uid, "status": "skipped_suppressed", "error": "", "timestamp": ts})
            continue

        try:
            await context.bot.copy_message(
                chat_id=uid,
                from_chat_id=original.chat.id,
                message_id=original.message_id
            )
            counts["delivered"] += 1
            log_writer.writerow({"user_id": uid, "status": "delivered", "error": "", "timestamp": ts})

        except Forbidden as e:
            counts["blocked"] += 1
            log_writer.writerow({"user_id": uid, "status": "blocked", "error": str(e), "timestamp": ts})
            new_suppressed_rows.append({"user_id": uid, "reason": "blocked", "date_added": datetime.date.today().isoformat()})

        except BadRequest as e:
            counts["deleted_or_invalid"] += 1
            log_writer.writerow({"user_id": uid, "status": "deleted_or_invalid", "error": str(e), "timestamp": ts})
            new_suppressed_rows.append({"user_id": uid, "reason": "deleted_or_invalid", "date_added": datetime.date.today().isoformat()})

        except RetryAfter as e:
            try:
                await asyncio.sleep(int(getattr(e, "retry_after", 5)))
                await context.bot.copy_message(
                    chat_id=uid,
                    from_chat_id=original.chat.id,
                    message_id=original.message_id
                )
                counts["delivered_after_retry"] += 1
                log_writer.writerow({"user_id": uid, "status": "delivered_after_retry", "error": "", "timestamp": ts})
            except Exception as e2:
                counts["error"] += 1
                log_writer.writerow({"user_id": uid, "status": "error", "error": f"RetryAfter-> {e2}", "timestamp": ts})

        except NetworkError as e:
            counts["network_error"] += 1
            log_writer.writerow({"user_id": uid, "status": "network_error", "error": str(e), "timestamp": ts})

        except Exception as e:
            counts["error"] += 1
            log_writer.writerow({"user_id": uid, "status": "error", "error": str(e), "timestamp": ts})

    # 5) Close log and update suppression
    log_file.close()
    _append_suppression(new_suppressed_rows)

    # 6) Summary to admin
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
    await query.edit_message_text(summary)

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

    await update.callback_query.edit_message_text(
        text=message,
        reply_markup=keyboard,
        parse_mode=constants.ParseMode.MARKDOWN,
        disable_web_page_preview=True
    )

async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # shared main menu text + keyboard
    message = (
        "🚀 *Solana100xcall — Premium Trading Signals* 🚀\n\n"
        "🚀 Trade smarter! Our AI scans 25,000+ tokens daily from LetsBonk, Pumpfun, Moonshot & top launchpads. 🤖 You get 30+ sniper-grade signals every day with instant buy options, 24/7.\n\n"
        "🎁 *Bonus for all plans:* 100 Top Killer Smart Money Wallets ready to import\n"
        "📦 Fully compatible with *BullX, Axiom, Padre, Gmgn* and all major DEX tools\n\n"
        "👇 Choose a plan to upgrade your trading edge"
    )

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("⚡ 1 Month VIP Access: 0.20 SOL • 20% OFF", callback_data="plan_1month")],
        [InlineKeyboardButton("👑 Lifetime VIP Access: 0.355 SOL • 20% OFF", callback_data="plan_lifetime")],
        [InlineKeyboardButton("📲 Join FREE Main Channel", url="https://t.me/Solana100xcall")],
        [InlineKeyboardButton("🥇 Real Results (Phanes Verified)", url="https://t.me/Solana100xcallBoard")],
        [
            InlineKeyboardButton("🤖 Help Bot", url="https://t.me/MyPremiumHelpBot"),
            InlineKeyboardButton("💬 Contact Support", callback_data="show_support")
        ]
    ])

    # If triggered by a button press (callback_query) → edit that message
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
            # update stored ids to the edited message
            context.chat_data["menu_message_id"] = query.message.message_id
            context.chat_data["menu_chat_id"] = query.message.chat.id
        except Exception:
            # fallback — send a fresh message and store it
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
        # Triggered by typing the command (e.g. /start or typing /menu)
        chat_id = update.effective_chat.id
        # delete the user's command message to avoid clutter
        if update.message:
            try:
                await update.message.delete()
            except Exception:
                pass

        menu_id = context.chat_data.get("menu_message_id")
        menu_chat = context.chat_data.get("menu_chat_id", chat_id)

        if menu_id:
            # try to edit the stored menu message
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
                # if edit fails (e.g. message was deleted) — send a new one and store it
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
            # no stored menu — send fresh and store
            menu_msg = await context.bot.send_message(
                chat_id=chat_id,
                text=message,
                reply_markup=keyboard,
                parse_mode=constants.ParseMode.MARKDOWN,
                disable_web_page_preview=True
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
    
    # ✅ Paste this line right here:
    logging.info(f"[storage] BASE_DIR={BASE_DIR} LOGS_DIR={LOGS_DIR} BACKUPS_DIR={BACKUPS_DIR}")
if __name__ == "__main__":
    main()
