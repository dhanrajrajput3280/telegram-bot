from telethon import TelegramClient, events, Button
from telethon.tl.functions.channels import GetParticipantRequest
import sqlite3
import random
from datetime import date

# =======================
# 🔐 TELEGRAM DETAILS (CHANGE ONLY THESE)
# =======================
api_id = 31272223
api_hash = "8062c4dfc7a6a95ffb00bdfa9cff269e"
bot_token = "8497845791:AAHYThI6Q5cCq1HNBZwP5Y9EVOCsbKBzZHE"

# =======================
# 👑 OWNER
# =======================
OWNER_ID = 6712059124

# =======================
# 🔒 CHANNEL (PUBLIC)
# =======================
FORCE_CHANNEL_LINK = "https://t.me/desiivirallhub"
FORCE_CHANNEL_ID = -1003522049325

# =======================
# 🤖 BOT CLIENT
# =======================
bot = TelegramClient("bot", api_id, api_hash).start(bot_token=bot_token)

# =======================
# 📦 DATABASE
# =======================
db = sqlite3.connect("database.db")
cursor = db.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    credits INTEGER,
    last_free_date TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS video_queue (
    user_id INTEGER,
    video_no INTEGER,
    position INTEGER,
    PRIMARY KEY (user_id, position)
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS shares (
    sharer_id INTEGER,
    joined_id INTEGER,
    PRIMARY KEY (sharer_id, joined_id)
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS pending_referrals (
    new_user_id INTEGER PRIMARY KEY,
    referrer_id INTEGER
)
""")

db.commit()

# =======================
# 🎬 VIDEO STORAGE
# =======================
VIDEOS = []

# =======================
# 🔒 JOIN CHECK
# =======================
async def is_joined(user_id):
    try:
        await bot(GetParticipantRequest(
            channel=FORCE_CHANNEL_ID,
            participant=user_id
        ))
        return True
    except:
        return False

# =======================
# 🎁 DAILY BONUS (SILENT)
# =======================
async def apply_daily_bonus(user_id):
    today = str(date.today())
    cursor.execute(
        "SELECT credits, last_free_date FROM users WHERE user_id=?",
        (user_id,)
    )
    row = cursor.fetchone()
    if not row:
        return
    credits, last_date = row
    if last_date != today:
        credits += 5
        cursor.execute(
            "UPDATE users SET credits=?, last_free_date=? WHERE user_id=?",
            (credits, today, user_id)
        )
        db.commit()

# =======================
# 🔒 JOIN MESSAGE
# =======================
async def send_join_message(event):
    await event.respond(
        "🚫 Access Locked\n\n"
        "To watch videos, please join our official channel.\n\n"
        "After joining, tap “Try Again”.",
        buttons=[
            [Button.url("📢 Join Channel", FORCE_CHANNEL_LINK)],
            [Button.inline("🔄 Try Again", b"try_again")]
        ]
    )

# =======================
# ▶️ START
# =======================
@bot.on(events.NewMessage(pattern=r"/start(?:\s+(\d+))?"))
async def start(event):
    user_id = event.sender_id
    today = str(date.today())
    ref = event.pattern_match.group(1)
    ref = int(ref) if ref else None

    cursor.execute("SELECT credits, last_free_date FROM users WHERE user_id=?", (user_id,))
    user = cursor.fetchone()

    if not user:
        cursor.execute("INSERT INTO users VALUES (?,?,?)", (user_id, 10, today))
        db.commit()
        credits = 10
        if ref and ref != user_id:
            cursor.execute(
                "INSERT OR IGNORE INTO pending_referrals VALUES (?,?)",
                (user_id, ref)
            )
            db.commit()
    else:
        credits, last = user
        if last != today:
            credits += 5
            cursor.execute(
                "UPDATE users SET credits=?, last_free_date=? WHERE user_id=?",
                (credits, today, user_id)
            )
            db.commit()

    await event.reply(
        "👋 Welcome to Viral Video Hub!\n\n"
        "🎬 Watch trending and viral videos easily.\n\n"
        f"💳 Your Available Credits: {'UNLIMITED' if user_id == OWNER_ID else credits}\n"
        "💡 1 credit = 1 video\n\n"
        "👇 Tap below to start watching.",
        buttons=[[Button.inline("▶️ Watch Video", b"watch")]]
    )

# =======================
# 🎥 OWNER VIDEO ADD
# =======================
@bot.on(events.NewMessage)
async def save_video(event):
    if event.sender_id == OWNER_ID and event.video:
        VIDEOS.append(event.video)
        await event.reply(f"✅ Video saved ({len(VIDEOS)})")

# =======================
# ▶️ TRY AGAIN
# =======================
@bot.on(events.CallbackQuery(data=b"try_again"))
async def try_again(event):
    user_id = event.sender_id

    if user_id != OWNER_ID and not await is_joined(user_id):
        await send_join_message(event)
        return

    await apply_daily_bonus(user_id)
    await watch_video(event)

# =======================
# ▶️ WATCH VIDEO
# =======================
@bot.on(events.CallbackQuery(data=b"watch"))
async def watch_video(event):
    user_id = event.sender_id

    if user_id != OWNER_ID and not await is_joined(user_id):
        await send_join_message(event)
        return

    await apply_daily_bonus(user_id)

    if not VIDEOS:
        await event.respond("⚠️ No videos available right now.")
        return

    if user_id != OWNER_ID:
        cursor.execute("SELECT credits FROM users WHERE user_id=?", (user_id,))
        credits = cursor.fetchone()[0]
        if credits <= 0:
            bot_username = (await bot.get_me()).username
            link = f"https://t.me/{bot_username}?start={user_id}"
            await event.respond(
                "🚫 Your credits are finished!\n\n"
                f"🔗 {link}"
            )
            return
        cursor.execute(
            "UPDATE users SET credits = credits - 1 WHERE user_id=?",
            (user_id,)
        )

    cursor.execute(
        "SELECT video_no FROM video_queue WHERE user_id=? ORDER BY position",
        (user_id,)
    )
    queue = [v[0] for v in cursor.fetchall()]

    if not queue:
        order = list(range(len(VIDEOS)))
        random.shuffle(order)
        for i, v in enumerate(order):
            cursor.execute(
                "INSERT INTO video_queue VALUES (?,?,?)",
                (user_id, v, i)
            )
        db.commit()
        queue = order

    video_no = queue[0]
    cursor.execute(
        "DELETE FROM video_queue WHERE user_id=? AND video_no=?",
        (user_id, video_no)
    )
    db.commit()

    await bot.send_file(
        user_id,
        VIDEOS[video_no],
        buttons=[
            [Button.inline("▶️ More Videos", b"watch")],
            [Button.inline("💳 Check Credits", b"credits")]
        ]
    )

# =======================
# 💳 CHECK CREDITS
# =======================
@bot.on(events.CallbackQuery(data=b"credits"))
async def check_credits(event):
    user_id = event.sender_id

    await apply_daily_bonus(user_id)

    if user_id == OWNER_ID:
        await event.respond("💳 Credits: UNLIMITED")
        return

    cursor.execute("SELECT credits FROM users WHERE user_id=?", (user_id,))
    credits = cursor.fetchone()[0]

    await event.respond(f"💳 Your Current Credits: {credits}")

# =======================
# 🚀 RUN
# =======================
print("🤖 Bot is running...")
bot.run_until_disconnected()

