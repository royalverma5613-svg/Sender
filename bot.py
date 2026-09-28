import asyncio
import sys
from pyrogram import Client, filters, idle
from pyrogram.types import ReplyKeyboardMarkup, KeyboardButton

# आपकी API और Token डिटेल्स
API_ID = 36568248
API_HASH = "6eac9c56e572771b858607474cc177e4"
BOT_TOKEN = "8999424037:AAGsD7V3VNBrOZ1DeaUm-qD49FT0JL6GqM4"
ADMIN_USERNAME = "egofiremax"
UPDATE_GROUP = "@data5k"

app = Client("my_advanced_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# डेटाबेस (मेमोरी में)
active_tasks = {}      
admin_state = {}       
stats = {"sent": 0, "failed": 0} 

# कीबोर्ड मेन्यू
main_menu = ReplyKeyboardMarkup(
    [
        [KeyboardButton("➕ Setup New Group")],
        [KeyboardButton("📊 Delivery Report"), KeyboardButton("⏹ Stop All Tasks")]
    ],
    resize_keyboard=True
)

# 1. 4-Hour Health Check Update Task
async def health_check():
    while True:
        try:
            msg = f"🟢 **Bot Status: Active & Working Fine**\n\nTotal Messages Sent: {stats['sent']}\nTotal Failed: {stats['failed']}\nActive Groups: {len(active_tasks)}"
            await app.send_message(UPDATE_GROUP, msg)
        except Exception as e:
            print(f"Update Group Error: {e}")
        await asyncio.sleep(4 * 3600) # 4 घंटे

# 2. ऑटोमैटिक मैसेज भेजने का लूप
async def auto_sender_loop(chat_id, message_text, interval):
    while True:
        try:
            await app.send_message(chat_id, message_text)
            stats["sent"] += 1
        except Exception as e:
            stats["failed"] += 1
            print(f"Failed to send to {chat_id}: {e}")
        
        await asyncio.sleep(interval)

# 3. Start Command (सिर्फ एडमिन के लिए)
@app.on_message(filters.command("start") & filters.private)
async def start_cmd(client, message):
    if message.from_user.username != ADMIN_USERNAME:
        return
    await message.reply_text("👋 Welcome Admin! Niche diye gaye Menu ka istemal karein:", reply_markup=main_menu)

# 4. Menu & State Management (इंटरैक्टिव चैट)
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
        await message.reply_text("✅ Message Saved!\n\n👉 Step 3: Ab timer set karein (Seconds mein bhejein, jaise 1 min = 60, 1 hour = 3600):")
    
    elif state.get("step") == 3:
        try:
            interval = int(text)
            group = state["group"]
            msg_text = state["msg"]
            
            task = asyncio.create_task(auto_sender_loop(group, msg_text, interval))
            active_tasks[group] = {"process": task}
            
            await app.send_message(UPDATE_GROUP, f"🆕 New Task Added!\nGroup: {group}\nInterval: {interval}s")
            
            await message.reply_text(f"🎉 Setup Complete! Bot ab har {interval} second mein {group} par message bhejega.", reply_markup=main_menu)
            admin_state[user_id] = {} 
            
        except ValueError:
            await message.reply_text("❌ Kripya sirf numbers bhejein (jaise 60 ya 120). Wapas try karein:")

# 5. Main Run Function (Render और Python 3.14+ के लिए फिक्स)
async def main():
    await app.start()
    print("🤖 Bot Started Successfully!")
    
    asyncio.create_task(health_check())
    
    await idle()
    await app.stop()

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(main())
    
