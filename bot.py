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
        self.wfile.write(b"Bot is active and running!")
    def log_message(self, format, *args):
        pass 

def start_dummy_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(('0.0.0.0', port), HealthCheckHandler)
    server.serve_forever()

threading.Thread(target=start_dummy_server, daemon=True).start()

# --- 2. BOT CONFIG ---
API_ID = 36568248
API_HASH = "6eac9c56e572771b858607474cc177e4"
BOT_TOKEN = "8999424037:AAGsD7V3VNBrOZ1DeaUm-qD49FT0JL6GqM4"
UPDATE_GROUP = "@data5k"
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
        return user.username.lower() in ADMIN_USERS
    return False

# --- 3. BACKGROUND TASKS ---
async def health_check():
    # Bot start hote hi thoda wait karke group me message bhejega
    await asyncio.sleep(5)
    try:
        await app.send_message(UPDATE_GROUP, "🚀 **Bot Server Successfully Started & Online!**")
    except Exception as e:
        print(f"Update error: {e}")

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

# --- 4. MESSAGE HANDLERS ---
@app.on_message(filters.command("start") & filters.private)
async def start_cmd(client, message):
    if is_admin(message.from_user):
        await message.reply_text("👋 Welcome Admin! Niche diye gaye Menu ka istemal karein:", reply_markup=main_menu)
    else:
        await message.reply_text("❌ Access Denied! You are not authorized.")

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

# --- 5. APP STARTUP EVENT ---
# Ye Pyrogram ka best tarika hai background task chalane ka
@app.on_message(filters.regex("start_health_check_dummy_message_ignore") & filters.me)
async def dummy_handler(client, message):
    pass

async def start_services():
    asyncio.create_task(health_check())

if __name__ == "__main__":
    print("🤖 Bot is starting...")
    # Health check ko alag thread me chalana takii Pyrogram block na ho
    loop = asyncio.get_event_loop()
    loop.create_task(health_check())
    
    # Ab Pyrogram ka official run method use karenge jo incoming messages catch karta hai
    app.run()
    
