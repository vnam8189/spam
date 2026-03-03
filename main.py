import os
import asyncio
import random
from flask import Flask
from threading import Thread
from telethon import TelegramClient, events
from telethon.tl.functions.channels import JoinChannelRequest
from telethon.errors import FloodWaitError, SessionPasswordNeededError

# --- CẤU HÌNH ---
API_ID = 36437338 
API_HASH = '18d34c7efc396d277f3db62baa078efc'
BOT_TOKEN = '8499499024:AAFSifEjBAKL2BSmanDDlXuRGh93zvZjM78'
ADMIN_ID = 7816353760 

SESSION_DIR = 'sessions'
GROUP_FILE = 'groups.txt'
MSG_FILE = 'ad_msg.txt' # File lưu nội dung tin nhắn

if not os.path.exists(SESSION_DIR): os.makedirs(SESSION_DIR)
if not os.path.exists(GROUP_FILE): open(GROUP_FILE, 'w').close()
if not os.path.exists(MSG_FILE): 
    with open(MSG_FILE, 'w', encoding='utf-8') as f: f.write("Nhóm chéo chất lượng ae vào chéo đi : Tham gia ngay (Link nhóm)")

ICONS = ["🔥", "🚀", "💎", "🧧", "🍀", "✨", "🎯", "⚡", "🌈", "💰"]
KEYWORDS_REPLY = ["bot", "link", "chéo", "admin", "đâu"]
is_spamming = False
last_messages = {} 
clones = {} 

# --- WEB SERVER ---
app = Flask('')
@app.route('/')
def home(): return "🤖 Bot Clone V8.7 is Live!"

def run_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port, use_reloader=False)

# --- QUẢN LÝ DỮ LIỆU ---
def get_ad_msg():
    with open(MSG_FILE, 'r', encoding='utf-8') as f: return f.read()

def load_groups():
    with open(GROUP_FILE, 'r') as f: return [line.strip() for line in f.readlines() if line.strip()]

def save_group(group):
    groups = load_groups()
    if group not in groups:
        with open(GROUP_FILE, 'a') as f: f.write(group + '\n')

def get_safe_text():
    inv = "".join(random.choices(['\u200b', '\u200c', '\u200d'], k=random.randint(4, 10)))
    return f"{random.choice(ICONS)} {get_ad_msg()} {random.choice(ICONS)}\n{inv}"

# --- MASTER BOT ---
master_bot = TelegramClient('master_bot', API_ID, API_HASH)

# Lệnh đổi nội dung tin nhắn
@master_bot.on(events.NewMessage(pattern='/setmsg'))
async def set_msg(event):
    if event.sender_id != ADMIN_ID: return
    try:
        new_msg = event.text.split(' ', 1)[1]
        with open(MSG_FILE, 'w', encoding='utf-8') as f: f.write(new_msg)
        await event.reply(f"✅ Đã cập nhật tin nhắn mới:\n`{new_msg}`")
    except: await event.reply("⚠️ Sử dụng: `/setmsg Nội dung tin nhắn`")

# Lệnh kiểm tra trạng thái
@master_bot.on(events.NewMessage(pattern='/status'))
async def status(event):
    if event.sender_id != ADMIN_ID: return
    sessions = [f for f in os.listdir(SESSION_DIR) if f.endswith('.session')]
    groups = load_groups()
    status_text = "🟢 Đang chạy" if is_spamming else "🔴 Đang dừng"
    msg = (f"📊 **BÁO CÁO HỆ THỐNG**\n"
           f"- Trạng thái: {status_text}\n"
           f"- Số lượng acc clone: {len(sessions)}\n"
           f"- Số lượng nhóm mục tiêu: {len(groups)}\n"
           f"- Danh sách nhóm: `{', '.join(groups) if groups else 'Trống'}`")
    await event.reply(msg)

# Giữ nguyên phần /add gốc của bạn
@master_bot.on(events.NewMessage(pattern='/add'))
async def add_account(event):
    if event.sender_id != ADMIN_ID: return
    async with master_bot.conversation(event.chat_id) as conv:
        try:
            await conv.send_message("📞 **Nhập số điện thoại (+84...):**")
            phone = (await conv.get_response()).text.strip()
            client = TelegramClient(os.path.join(SESSION_DIR, f"{phone}.session"), API_ID, API_HASH)
            await client.connect()
            if not await client.is_user_authorized():
                await client.send_code_request(phone)
                await conv.send_message("📩 **Nhập OTP:**")
                otp = (await conv.get_response()).text.strip()
                try:
                    await client.sign_in(phone, otp)
                except SessionPasswordNeededError:
                    await conv.send_message("🔒 **Nhập 2FA:**")
                    await client.sign_in(password=(await conv.get_response()).text.strip())
            await conv.send_message(f"✅ Đã nạp acc: `{phone}`")
            await client.disconnect()
        except Exception as e: await conv.send_message(f"❌ Lỗi: {str(e)}")

# Lệnh cho toàn bộ acc Join nhóm
@master_bot.on(events.NewMessage(pattern='/join'))
async def join_groups(event):
    if event.sender_id != ADMIN_ID: return
    targets = load_groups()
    sessions = [f for f in os.listdir(SESSION_DIR) if f.endswith('.session')]
    if not targets or not sessions: return await event.reply("❌ Thiếu group hoặc acc.")
    
    await event.reply(f"🔄 Đang cho {len(sessions)} acc join {len(targets)} nhóm. Vui lòng đợi...")
    for s in sessions:
        c = TelegramClient(os.path.join(SESSION_DIR, s), API_ID, API_HASH)
        await c.connect()
        for t in targets:
            try: await c(JoinChannelRequest(t)); await asyncio.sleep(2)
            except: pass
        await c.disconnect()
    await event.reply("✅ Đã hoàn thành lệnh Join!")

# --- LOGIC SPAM ---
async def start_reply_handler(client):
    @client.on(events.NewMessage(incoming=True))
    async def handler(event):
        if event.is_private or not is_spamming: return
        targets = load_groups()
        chat = await event.get_chat()
        username = getattr(chat, 'username', '')
        if username and any(username in g for g in targets):
            if any(word in (event.text or "").lower() for word in KEYWORDS_REPLY):
                await asyncio.sleep(random.randint(3, 8))
                try: await event.reply(f"🤖 {get_ad_msg()}")
                except: pass

async def run_spam_loop():
    global is_spamming
    while is_spamming:
        targets = load_groups()
        session_files = [f for f in os.listdir(SESSION_DIR) if f.endswith('.session')]
        for target in targets:
            if not is_spamming: break
            s_name = random.choice(session_files)
            if s_name not in clones:
                c = TelegramClient(os.path.join(SESSION_DIR, s_name), API_ID, API_HASH)
                try:
                    await c.connect()
                    if await c.is_user_authorized():
                        await start_reply_handler(c)
                        clones[s_name] = c
                except: continue
            client = clones.get(s_name)
            if client:
                try:
                    m_key = (s_name, target)
                    if m_key in last_messages:
                        try: await client.delete_messages(target, [last_messages[m_key]])
                        except: pass
                    sent = await client.send_message(target, get_safe_text())
                    last_messages[m_key] = sent.id
                except: pass
            await asyncio.sleep(random.randint(90, 160))
        await asyncio.sleep(300)

@master_bot.on(events.NewMessage(pattern='/addgroup'))
async def add_g(event):
    if event.sender_id == ADMIN_ID:
        try:
            group = event.text.split(' ', 1)[1].strip().replace('@', '')
            save_group(group); await event.reply(f"✅ Đã thêm: {group}")
        except: pass

@master_bot.on(events.NewMessage(pattern='/spam'))
async def spam_cmd(event):
    global is_spamming
    if event.sender_id == ADMIN_ID:
        is_spamming = True
        asyncio.create_task(run_spam_loop()); await event.reply("🚀 Start!")

@master_bot.on(events.NewMessage(pattern='/stop'))
async def stop_cmd(event):
    if event.sender_id == ADMIN_ID:
        is_spamming = False; await event.reply("🛑 Stop!")

async def main():
    await master_bot.start(bot_token=BOT_TOKEN)
    print("✅ Bot Online!"); await master_bot.run_until_disconnected()

if __name__ == "__main__":
    Thread(target=run_web, daemon=True).start()
    try: asyncio.run(main())
    except:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(main())
