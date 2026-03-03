import os
import asyncio
import random
import string
from flask import Flask
from threading import Thread
from telethon import TelegramClient, events, errors
from telethon.tl.functions.channels import JoinChannelRequest
from telethon.errors import FloodWaitError, PeerFloodError

# --- CẤU HÌNH ---
API_ID = 36437338 
API_HASH = '18d34c7efc396d277f3db62baa078efc'
BOT_TOKEN = '8499499024:AAFSifEjBAKL2BSmanDDlXuRGh93zvZjM78'
ADMIN_ID = 7816353760 

SESSION_DIR = 'sessions'
GROUP_FILE = 'groups.txt'

if not os.path.exists(SESSION_DIR): os.makedirs(SESSION_DIR)
if not os.path.exists(GROUP_FILE): open(GROUP_FILE, 'w').close()

# Biến toàn cục
AD_MESSAGE = "Nhóm chéo chất lượng ae vào chéo đi : Tham gia ngay (Link nhóm)"
ICONS = ["🔥", "🚀", "💎", "🧧", "🍀", "✨", "🎯", "⚡", "🌈", "💰"]
KEYWORDS_REPLY = ["bot", "link", "chéo", "admin", "đâu"]
is_spamming = False
last_messages = {} # Lưu { (session, chat_id): message_id } để xóa

# --- WEB SERVER (KEEP ALIVE) ---
app = Flask('')
@app.route('/')
def home(): return "🤖 Bot Clone Safe-Mode V7.0 is Online!"
def run_web(): app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))

# --- QUẢN LÝ FILE ---
def load_groups():
    with open(GROUP_FILE, 'r') as f:
        return [line.strip() for line in f.readlines() if line.strip()]

def save_group(group):
    groups = load_groups()
    if group not in groups:
        with open(GROUP_FILE, 'a') as f: f.write(group + '\n')

def remove_group(group):
    groups = load_groups()
    if group in groups:
        groups.remove(group)
        with open(GROUP_FILE, 'w') as f: f.write('\n'.join(groups) + '\n')

def get_safe_text():
    invisible = "".join(random.choices(['\u200b', '\u200c', '\u200d'], k=random.randint(4, 8)))
    icon = random.choice(ICONS)
    return f"{icon} {AD_MESSAGE} {icon}\n{invisible}"

# --- MASTER BOT & CLONES ---
master_bot = TelegramClient('master_bot', API_ID, API_HASH)
clones = {} # Lưu trữ các client clone đang chạy

async def start_reply_handler(client, session_name):
    """Lắng nghe và trả lời tự động cho từng clone"""
    @client.on(events.NewMessage(incoming=True))
    async def handler(event):
        if event.is_private: return
        msg_text = event.text.lower() if event.text else ""
        if any(word in msg_text for word in KEYWORDS_REPLY):
            await asyncio.sleep(random.randint(3, 7)) # Giả lập đang gõ
            try:
                await event.reply(f"Chào bạn, {AD_MESSAGE}")
                print(f"📩 {session_name} đã reply tại {event.chat_id}")
            except: pass

# --- CORE SPAM LOGIC ---
async def run_spam_loop():
    global is_spamming, last_messages
    while is_spamming:
        targets = load_groups()
        session_files = [f for f in os.listdir(SESSION_DIR) if f.endswith('.session')]
        
        if not targets or not session_files:
            await asyncio.sleep(10)
            continue

        random.shuffle(targets)
        for target in targets:
            if not is_spamming: break
            
            # Chọn clone ngẫu nhiên từ những clone đã kết nối
            s_name = random.choice(session_files)
            if s_name not in clones:
                client = TelegramClient(os.path.join(SESSION_DIR, s_name), API_ID, API_HASH)
                try:
                    await client.connect()
                    if await client.is_user_authorized():
                        await start_reply_handler(client, s_name)
                        clones[s_name] = client
                    else: continue
                except: continue
            
            client = clones[s_name]
            try:
                # 1. Xóa tin nhắn cũ của clone này trong nhóm này
                msg_key = (s_name, target)
                if msg_key in last_messages:
                    try:
                        await client.delete_messages(target, [last_messages[msg_key]])
                    except: pass
                
                # 2. Gửi tin nhắn mới
                sent_msg = await client.send_message(target, get_safe_text())
                last_messages[msg_key] = sent_msg.id
                print(f"✅ {s_name} -> {target}")

            except FloodWaitError as e:
                print(f"⚠️ {s_name} bị giới hạn, nghỉ {e.seconds}s")
                await asyncio.sleep(e.seconds)
            except Exception as e:
                print(f"❌ Lỗi tại {target}: {e}")
            
            # Delay an toàn giữa các nhóm
            await asyncio.sleep(random.randint(70, 110))

        # Nghỉ sau 1 vòng
        if is_spamming:
            await asyncio.sleep(random.randint(300, 600))

# --- COMMANDS ---
@master_bot.on(events.NewMessage(pattern='/start'))
async def start(event):
    if event.sender_id != ADMIN_ID: return
    menu = (
        "🛡️ **HỆ THỐNG CLONE V7.0 PRO** 🛡️\n"
        "━━━━━━━━━━━━━━━━━━━━━━━\n"
        "🚀 `/spam` : Bắt đầu rải tin & Auto-Reply\n"
        "🛑 `/stop` : Dừng hệ thống\n"
        "📱 `/list` : Xem danh sách Clone\n"
        "👥 `/addgroup [link]` : Thêm nhóm\n"
        "⚙️ `/setmsg [nội dung]` : Đổi tin nhắn\n"
        "📊 `/status` : Kiểm tra trạng thái\n"
        "━━━━━━━━━━━━━━━━━━━━━━━"
    )
    await event.reply(menu)

@master_bot.on(events.NewMessage(pattern='/spam'))
async def spam_cmd(event):
    global is_spamming
    if event.sender_id != ADMIN_ID: return
    if is_spamming: return await event.reply("✅ Hệ thống đang chạy rồi.")
    is_spamming = True
    asyncio.create_task(run_spam_loop())
    await event.reply("🚀 **Đã kích hoạt chế độ Spam & Auto-Reply!**")

@master_bot.on(events.NewMessage(pattern='/stop'))
async def stop_cmd(event):
    global is_spamming
    is_spamming = False
    await event.reply("🛑 **Đã dừng gửi tin.**")

@master_bot.on(events.NewMessage(pattern='/setmsg'))
async def set_msg(event):
    global AD_MESSAGE
    if event.sender_id != ADMIN_ID: return
    try:
        AD_MESSAGE = event.text.split('/setmsg ', 1)[1]
        await event.reply(f"✅ Cập nhật nội dung thành công.")
    except: await event.reply("⚠️ Nhập: `/setmsg [nội dung]`")

@master_bot.on(events.NewMessage(pattern='/addgroup'))
async def add_group_cmd(event):
    if event.sender_id != ADMIN_ID: return
    try:
        group = event.text.split(' ', 1)[1].strip()
        save_group(group)
        await event.reply(f"✅ Đã thêm: `{group}`")
    except: await event.reply("⚠️ Nhập: `/addgroup link`")

@master_bot.on(events.NewMessage(pattern='/status'))
async def status(event):
    if event.sender_id != ADMIN_ID: return
    stt = "🟢 Đang chạy" if is_spamming else "🔴 Đang dừng"
    await event.reply(f"📊 **Trạng thái:** {stt}\n👥 **Clone online:** {len(clones)}\n📁 **Nhóm:** {len(load_groups())}")

# --- KHỞI CHẠY ---
async def main():
    await master_bot.start(bot_token=BOT_TOKEN)
    print("Master Bot is ready!")
    await master_bot.run_until_disconnected()

if __name__ == "__main__":
    Thread(target=run_web, daemon=True).start()
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
    
