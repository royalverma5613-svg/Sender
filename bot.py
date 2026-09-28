import os
import asyncio
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from pyrogram import Client, filters
from pyrogram.types import ReplyKeyboardMarkup, KeyboardButton

# --- 1. RENDER PORT FIX ---
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is active!")

def start_dummy_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(('0.0.0.0', port), HealthCheckHandler)
    server.serve_forever()

threading.Thread(target=start_dummy_server, daemon=True).start()

# --- 2. BOT CREDENTIALS & ADMINS ---
API_ID = 36568248
API_HASH = "6eac9c56e572771b858607474cc177e4"
BOT_TOKEN = "8999424037:AAGsD7V3VNBrOZ1DeaUm-qD49FT0JL6GqM4"
UPDATE_GROUP = "@data5k"

# Aapke aur dost ke usernames (chote aksharon mein)
ADMIN_USERS = ["egofiremax", "vcfboss3k"]

app = Client("my_advanced_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

active_tasks = {}      
admin_state = {}       
stats = {"sent": 0, "failed": 0} 

main_menu = ReplyKeyboardMarkup(
    [
        [KeyboardButton("➕ Setup New Group")],
        [KeyboardButton("📊 Delivery Report"), KeyboardButton("⏹ Stop All Tasks")]
    ],
    resize_keyboard=True
)

def is_admin(user):
    if user and user.username:
        print(f"DEBUG: Incoming user username -> {user.username}") # Render logs mein dikhega
        return user.username.lower() in [u.lower() for u in ADMIN_USERS]
    print(f"DEBUG: User has no username set! User ID: {user.id if user else 'Unknown'}")
    return False

# --- 3. STARTUP & HEALTH CHECK ---
async def health_check():
    try:
        await app.send_message(UPDATE_GROUP, "🚀 **Bot Server Successfully Started & Online!**")
    except Exception:
        pass

    while True:
        await asyncio.sleep(4 * 3600)
        try:
            msg = f"🟢 **Bot Status: Active**\nSent: {stats['sent']}\nFailed: {stats['failed']}\nActive Tasks: {len(active_tasks)}"
            await app.send_message(UPDATE_GROUP, msg)
        except Exception:
            pass

async def auto_sender_loop(chat_id, message_text, interval):
    while True:
        await asyncio.sleep(interval)
        try:
            await app.send_message(chat_id, message_text)
            stats["sent"] += 1
        except Exception:
            stats["failed"] += 1

@app.on_message(filters.command("start") & filters.private)
async def start_cmd(client, message):
    user = message.from_user
    print(f"DEBUG /start command received from: {user.first_name} (@{user.username}, ID: {user.id})")
    
    if is_admin(user):
        await message.reply_text("👋 Welcome Admin! Niche diye gaye Menu ka istemal karein:", reply_markup=main_menu)
    else:
        username_str = f"@{user.username}" if user.username else "No Username"
        await message.reply_text(f"❌ Access Denied!\nAapka username: {username_str}\nAap admin list mein nahi hain.")

@app.on_message(filters.text & filters.private)
async def handle_text(client, message):
    if not is_admin(message.from_user):
        return

    text = message.text
    user_id = message.from_user.id

    if text == "➕ Setup New Group":
        admin_state[user_id] = {"step": 1}
        await message.reply_text("👉 Step 1: Group Username (@group) ya Chat ID bhejein:")
        return
    elif text == "📊 Delivery Report":
        report = f"📈 **Report**\n✅ Sent: {stats['sent']}\n❌ Failed: {stats['failed']}\n🔁 Active Tasks: {len(active_tasks)}"
        await message.reply_text(report, reply_markup=main_menu)
        return
    elif text == "⏹ Stop All Tasks":
        for task in active_tasks.values():
            task["process"].cancel()
        active_tasks.clear()
        await message.reply_text("🛑 Sabhi auto-messages rok diye gaye hain.", reply_markup=main_menu)
        return

    state = admin_state.get(user_id, {})
    if state.get("step") == 1:
        state["group"] = text
        state["step"] = 2
        await message.reply_text(f"✅ Group: {text}\n👉 Step 2: Apna Message bhejein:")
    elif state.get("step") == 2:
        state["msg"] = text
        state["step"] = 3
        await message.reply_text("✅ Saved!\n👉 Step 3: Timer (seconds mein dalein, jaise 60):")
    elif state.get("step") == 3:
        try:
            interval = int(text)
            group = state["group"]
            msg_text = state["msg"]
            task = asyncio.create_task(auto_sender_loop(group, msg_text, interval))
            active_tasks[group] = {"process": task}
            await app.send_message(UPDATE_GROUP, f"🆕 Task Added: {group} ({interval}s)")
            await message.reply_text("🎉 Setup Complete!", reply_markup=main_menu)
            admin_state[user_id] = {} 
        except ValueError:
            await message.reply_text("❌ Kripya sirf number dalein:")

# --- 4. MAIN RUNNER ---
async def main():
    await app.start()
    asyncio.create_task(health_check())
    
    try:
        while True:
            await asyncio.sleep(3600)
    except asyncio.CancelledError:
        pass
    finally:
        await app.stop()

if __name__ == "__main__":
    asyncio.run(main())
    
