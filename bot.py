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

# DATABASE: Stores group_id -> {process, interval, msg_id, fallback_text, from_chat_id}
active_tasks = {}      
admin_state = {}       
stats = {"sent": 0, "failed": 0} 

main_menu = ReplyKeyboardMarkup(
    [
        [KeyboardButton("➕ Setup New Group"), KeyboardButton("📋 Active Groups")],
        [KeyboardButton("📢 Broadcast to All")],
        [KeyboardButton("📊 Delivery Report"), KeyboardButton("⏹ Stop All Tasks")]
    ],
    resize_keyboard=True
)

def is_admin(user):
    if user and user.username:
        return user.username.lower() in ADMIN_USERS
    return False

# --- SMART SENDER (Photo -> Text Fallback Logic) ---
async def smart_send(client, target_chat, from_chat, msg_id, fallback_text):
    try:
        # Pura message (Photo + Text) copy karke bhejega
        await client.copy_message(chat_id=target_chat, from_chat_id=from_chat, message_id=msg_id)
        return True
    except Exception as e:
        # Agar group me photo allowed nahi hai, toh sirf text bhejega
        if fallback_text:
            try:
                await client.send_message(chat_id=target_chat, text=fallback_text)
                return True
            except Exception:
                pass
        return False

# --- 3. BACKGROUND TASKS ---
async def health_check():
    await asyncio.sleep(5)
    try:
        await app.send_message(UPDATE_GROUP, "🚀 **Bot Server Successfully Started & Online!**")
    except Exception:
        pass

    while True:
        await asyncio.sleep(4 * 3600)
        try:
            msg = f"🟢 **Bot Status: Active**\nSent: {stats['sent']}\nFailed: {stats['failed']}\nActive Groups: {len(active_tasks)}"
            await app.send_message(UPDATE_GROUP, msg)
        except Exception:
            pass

async def auto_sender_loop(chat_id, from_chat, msg_id, fallback_text, interval):
    while True:
        await asyncio.sleep(interval)
        success = await smart_send(app, chat_id, from_chat, msg_id, fallback_text)
        if success:
            stats["sent"] += 1
        else:
            stats["failed"] += 1

# --- 4. MESSAGE HANDLERS ---
@app.on_message(filters.command("start") & filters.private)
async def start_cmd(client, message):
    if is_admin(message.from_user):
        await message.reply_text("👋 Welcome Admin! Niche diye gaye Menu ka istemal karein:", reply_markup=main_menu)
    else:
        await message.reply_text("❌ Access Denied! You are not authorized.")

# filters.text hata diya taaki Photo/Video sab catch ho jaye
@app.on_message(~filters.command("start") & filters.private)
async def handle_messages(client, message):
    if not is_admin(message.from_user):
        return

    # Button text check karne ke liye safe extraction
    btn_text = message.text if message.text else ""
    user_id = message.from_user.id

    # --- MENU ACTIONS ---
    if btn_text == "➕ Setup New Group":
        admin_state[user_id] = {"step": 1}
        await message.reply_text("👉 Step 1: Group Username (@group) ya Chat ID bhejein:")
        return
        
    elif btn_text == "📋 Active Groups":
        if not active_tasks:
            await message.reply_text("🚫 Abhi tak koi group set nahi kiya gaya hai.")
            return
        
        list_msg = "📋 **Active Groups Record:**\n\n"
        for i, (grp, data) in enumerate(active_tasks.items(), 1):
            list_msg += f"{i}. **{grp}** (Timer: {data['interval']}s)\n"
        await message.reply_text(list_msg, reply_markup=main_menu)
        return
        
    elif btn_text == "📢 Broadcast to All":
        if not active_tasks:
            await message.reply_text("🚫 Aapke paas koi active group nahi hai jise message bheja ja sake.")
            return
        admin_state[user_id] = {"step": "broadcast"}
        await message.reply_text("📢 **Broadcast Mode:**\n\nApna Message ya Photo bhejein. Yeh turant sabhi Active Groups mein chala jayega:")
        return

    elif btn_text == "📊 Delivery Report":
        report = f"📈 **Report**\n✅ Sent: {stats['sent']}\n❌ Failed: {stats['failed']}\n🔁 Active Groups: {len(active_tasks)}"
        await message.reply_text(report, reply_markup=main_menu)
        return
        
    elif btn_text == "⏹ Stop All Tasks":
        for task in active_tasks.values():
            task["process"].cancel()
        active_tasks.clear()
        await message.reply_text("🛑 Sabhi auto-messages rok diye gaye hain.", reply_markup=main_menu)
        return

    # --- STATE MACHINE (Steps Logic) ---
    state = admin_state.get(user_id, {})
    
    # Broadcast Mode Execution
    if state.get("step") == "broadcast":
        fallback = message.text or message.caption or ""
        msg_id = message.id
        from_chat = message.chat.id
        sent_count = 0
        
        await message.reply_text("⏳ Sending broadcast to all groups...")
        for grp in active_tasks.keys():
            success = await smart_send(app, grp, from_chat, msg_id, fallback)
            if success: sent_count += 1
            
        await message.reply_text(f"✅ Broadcast Complete!\nSuccessfully sent to {sent_count}/{len(active_tasks)} groups.", reply_markup=main_menu)
        admin_state[user_id] = {}
        return

    # Normal Setup Mode
    if state.get("step") == 1:
        state["group"] = btn_text
        state["step"] = 2
        await message.reply_text(f"✅ Group: {btn_text}\n👉 Step 2: Apna Message ya Photo bhejein:")
        
    elif state.get("step") == 2:
        # Photo/Text ko database ke liye save kar rahe hain
        state["msg_id"] = message.id
        state["from_chat_id"] = message.chat.id
        state["fallback_text"] = message.text or message.caption or ""
        state["step"] = 3
        await message.reply_text("✅ Message/Media Saved!\n👉 Step 3: Timer (seconds mein dalein, jaise 60):")
        
    elif state.get("step") == 3:
        try:
            interval = int(btn_text)
            group = state["group"]
            msg_id = state["msg_id"]
            from_chat = state["from_chat_id"]
            fallback = state["fallback_text"]
            
            # Start background task
            task = asyncio.create_task(auto_sender_loop(group, from_chat, msg_id, fallback, interval))
            
            # Save to records
            active_tasks[group] = {
                "process": task,
                "interval": interval,
                "msg_id": msg_id,
                "from_chat_id": from_chat,
                "fallback_text": fallback
            }
            
            await app.send_message(UPDATE_GROUP, f"🆕 New Setup: {group} ({interval}s)")
            await message.reply_text("🎉 Setup Complete!", reply_markup=main_menu)
            admin_state[user_id] = {} 
        except ValueError:
            await message.reply_text("❌ Kripya sirf number dalein:")

# --- 5. APP STARTUP EVENT ---
async def start_services():
    asyncio.create_task(health_check())

if __name__ == "__main__":
    print("🤖 Bot is starting...")
    loop = asyncio.get_event_loop()
    loop.create_task(health_check())
    app.run()
            
