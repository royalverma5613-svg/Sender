import os
import sys
import asyncio
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from pyrogram import Client, filters
from pyrogram.types import ReplyKeyboardMarkup, KeyboardButton

# --- 1. RENDER PORT FIX (Web Service Dummy Server) ---
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is active and running 24x7!")

def start_dummy_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(('0.0.0.0', port), HealthCheckHandler)
    server.serve_forever()

threading.Thread(target=start_dummy_server, daemon=True).start()

# --- 2. BOT CREDENTIALS ---
API_ID = 36568248
API_HASH = "6eac9c56e572771b858607474cc177e4"
BOT_TOKEN = "8999424037:AAGsD7V3VNBrOZ1DeaUm-qD49FT0JL6GqM4"
ADMIN_USERNAME = "egofiremax"
UPDATE_GROUP = "@data5k"

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

# --- 3. STARTUP & HEALTH CHECK ---
async def health_check():
    # jaise hi server start hoga, update group mein turant message jayega
    try:
        await app.send_message(UPDATE_GROUP, "🚀 **Bot Server Successfully Started & Online!**\n\nBot ab 24x7 active hai aur kaam karne ke liye taiyar hai.")
    except Exception as e:
        print(f"Startup message error: {e}")

    # Har 4 ghante mein status update
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
    if message.from_user.username == ADMIN_USERNAME:
        await message.reply_text("👋 Welcome Admin!", reply_markup=main_menu)

@app.on_message(filters.text & filters.private)
async def handle_text(client, message):
    if message.from_user.username != ADMIN_USERNAME:
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
        exceptValueError:
            await message.reply_text("❌ Kripya sirf number dalein:")

# --- 4. MAIN RUNNER (PYTHON 3.14 SAFE) ---
async def main():
    print("🤖 Starting Pyrogram Client...")
    await app.start()
    print("🤖 Bot is Online!")
    
    # Startup message aur health check task shuru karna
    asyncio.create_task(health_check())
    
    # Safe infinite loop (replaces pyrogram.idle() to avoid crash)
    try:
        while True:
            await asyncio.sleep(3600)
    except asyncio.CancelledError:
        pass
    finally:
        await app.stop()

if __name__ == "__main__":
    asyncio.run(main())
    
