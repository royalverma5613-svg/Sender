import os
import asyncio
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from pyrogram import Client, filters
from pyrogram.types import ReplyKeyboardMarkup, KeyboardButton

# 1. Render Port Binding ke liye Dummy HTTP Server (Web Service Error Fix)
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is active and running 24x7!")

def start_dummy_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(('0.0.0.0', port), HealthCheckHandler)
    server.serve_forever()

# Background mein HTTP server start kar rahe hain taaki Render khush rahe
threading.Thread(target=start_dummy_server, daemon=True).start()

# 2. Bot Credentials & Settings
API_ID = 36568248
API_HASH = "6eac9c56e572771b858607474cc177e4"
BOT_TOKEN = "8999424037:AAGsD7V3VNBrOZ1DeaUm-qD49FT0JL6GqM4"
ADMIN_USERNAME = "egofiremax"
UPDATE_GROUP = "@data5k"

app = Client("my_advanced_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Databases & Stats
active_tasks = {}      
admin_state = {}       
stats = {"sent": 0, "failed": 0} 

# Main Keyboard Menu
main_menu = ReplyKeyboardMarkup(
    [
        [KeyboardButton("➕ Setup New Group")],
        [KeyboardButton("📊 Delivery Report"), KeyboardButton("⏹ Stop All Tasks")]
    ],
    resize_keyboard=True
)

# 3. 4-Hour Health Check Update Task
async def health_check():
    # Thoda wait karke pehla update bhejenge
    await asyncio.sleep(10)
    while True:
        try:
            msg = f"🟢 **Bot Status: Active & Working Fine**\n\nTotal Messages Sent: {stats['sent']}\nTotal Failed: {stats['failed']}\nActive Groups: {len(active_tasks)}"
            await app.send_message(UPDATE_GROUP, msg)
        except Exception as e:
            print(f"Update Group Error: {e}")
        await asyncio.sleep(4 * 3600) # Har 4 ghante mein update

# 4. Auto Sender Loop (Timer ke hisab se message bhejne wala lूप)
async def auto_sender_loop(chat_id, message_text, interval):
    while True:
        await asyncio.sleep(interval)
        try:
            await app.send_message(chat_id, message_text)
            stats["sent"] += 1
        except Exception as e:
            stats["failed"] += 1
            print(f"Failed to send to {chat_id}: {e}")

# 5. Start Command (Sirf Admin ke liye)
@app.on_message(filters.command("start") & filters.private)
async def start_cmd(client, message):
    if message.from_user.username != ADMIN_USERNAME:
        return
    await message.reply_text("👋 Welcome Admin! Niche diye gaye Menu ka istemal karein:", reply_markup=main_menu)

# 6. Interactive Menu & State Management
@app.on_message(filters.text & filters.private)
async def handle_text(client, message):
    if message.from_user.username != ADMIN_USERNAME:
        return

    text = message.text
    user_id = message.from_user.id

    if text == "➕ Setup New Group":
        admin_state[user_id] = {"step": 1}
        await message.reply_text("👉 Step 1: Kripya Group ka Username (jaise @groupname) ya Chat ID bhejein:")
        return

    elif text == "📊 Delivery Report":
        report = f"📈 **Delivery Report**\n\n✅ Sent: {stats['sent']}\n❌ Failed: {stats['failed']}\n🔁 Active Tasks: {len(active_tasks)}"
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
        await message.reply_text(f"✅ Group set: {text}\n\n👉 Step 2: Ab is group ke liye apna Message type karke bhejein:")
    
    elif state.get("step") == 2:
        state["msg"] = text
        state["step"] = 3
        await message.reply_text("✅ Message Saved!\n\n👉 Step 3: Ab timer set karein (Seconds mein bhejein, jaise 5 sec ke liye 5, 1 min ke liye 60):")
    
    elif state.get("step") == 3:
        try:
            interval = int(text)
            group = state["group"]
            msg_text = state["msg"]
            
            # Background task create karna
            task = asyncio.create_task(auto_sender_loop(group, msg_text, interval))
            active_tasks[group] = {"process": task}
            
            await app.send_message(UPDATE_GROUP, f"🆕 New Task Added!\nGroup: {group}\nInterval: {interval}s")
            
            await message.reply_text(f"🎉 Setup Complete! Bot ab har {interval} second mein {group} par message bhejega.", reply_markup=main_menu)
            admin_state[user_id] = {} 
            
        except ValueError:
            await message.reply_text("❌ Kripya sirf numbers bhejein (jaise 5 ya 60). Wapas try karein:")

# 7. Background Health Check Init on Start
@app.on_raw_update()
async def startup_hook(client, update, users, chats):
    pass

# Main Runner (Clean & Error-Free)
if __name__ == "__main__":
    print("🤖 Bot is starting up...")
    # Background health check task start karne ke liye client start hone par event add karenge
    app.start()
    asyncio.get_event_loop().create_task(health_check())
    print("🤖 Bot Started Successfully & HTTP Server is running!")
    
    # Idle block to keep script running
    from pyrogram import idle
    idle()
    app.stop()
    
