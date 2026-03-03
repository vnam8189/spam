import os
import asyncio
import random
from flask import Flask
from threading import Thread
from telethon import TelegramClient, events, errors
from telethon.tl.functions.channels import JoinChannelRequest
from telethon.errors import FloodWaitError

# --- CẤU HÌNH ---
API_ID = 36437338 
API_HASH = '18d34c7efc396d277f3db62baa078efc'
BOT_TOKEN = '8499499024:AAFSifEjBAKL2BSmanDDlXuRGh93zvZjM78'
ADMIN_ID = 7816353760 

SESSION_DIR = 'sessions'
GROUP_FILE = 'groups.txt'

if not os.path.exists(SESSION_DIR): os.makedirs(SESSION_DIR)
if not os.path.exists(GROUP_FILE): open(GROUP_FILE, 'w').close()

AD_MESSAGE = "Nhóm chéo chất lượng ae vào chéo đi : Tham gia ngay (Link nhóm)"
ICONS = ["🔥", "🚀", "💎", "🧧", "🍀", "✨", "🎯", "⚡", "🌈", "💰"]
KEYWORDS_REPLY = ["bot", "link", "chéo", "admin", "đâu"]
is_spamming = False
last_messages = {} # Lưu { (session_name, group_username): message_id }

# --- WEB SERVER ---
app = Flask('')
@app.route('/')
def home(): return "🤖 Bot Clone V7.1 - Active"
def run_web(): app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))

# --- QUẢN LÝ DANH SÁCH NHÓM ---
def load_groups():
    with open(GROUP_FILE, 'r') as f:
        # Lọc bỏ dòng trống và khoảng trắng
        return [line.strip() for line in f.readlines() if line.strip()]

def save_group(group):
    groups = load_groups()
    if group not in groups:
        with open(GROUP_FILE, 'a') as f: f.write(group + '\n')

# --- LOGIC CHÍNH ---
master_bot = TelegramClient('master_bot', API_ID, API_HASH)
clones = {} 

async def start_reply_handler(client, session_name):
    @client.on(events.NewMessage(incoming=True))
    async def handler(event):
        if event.is_private or not is_spamming: return
        
        # Chỉ trả lời nếu tin nhắn đến từ một trong các nhóm trong groups.txt
        current_groups = load_groups()
        # Kiểm tra xem nhóm hiện tại có trong danh sách mục tiêu không
        is_target = False
        if event.chat:
            username = getattr(event.chat, 'username', None)
            if username and any(username in g for g in current_groups):
                is_target = True

        if is_target and any(word in (event.text or "").lower() for word in KEYWORDS_REPLY):
            await asyncio.sleep(random.randint(3, 10))
            try:
                await event.reply(f"Chào bạn, {AD_MESSAGE}")
            except: pass

async def run_spam_loop():
    global is_spamming, last_messages
    while is_spamming:
        targets = load_groups() # Luôn load lại danh sách mới nhất
        session_files = [f for f in os.listdir(SESSION_DIR) if f.endswith('.session')]
        
        if not targets:
            print("⚠️ Danh sách nhóm trống. Đang chờ...")
            await asyncio.sleep(30)
            continue

        for target in targets:
            if not is_spamming: break
            
            # Chọn ngẫu nhiên 1 clone để gửi
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
                # 1. Xóa tin cũ trong nhóm này của clone này
                msg_key = (s_name, target)
                if msg_key in last_messages:
                    try:
                        await client.delete_messages(target, [last_messages[msg_key]])
                    except: pass
                
                # 2. Gửi tin mới
                invisible = "".join(random.choices(['\u200b', '\u200c'], k=5))
                text = f"{random.choice(ICONS)} {AD_MESSAGE} {random.choice(ICONS)}\n{invisible}"
                
                sent_msg = await client.send_message(target, text)
                last_messages[msg_key] = sent_msg.id
                print(f"✅ Gửi thành công tới {target} bởi {s_name}")

            except FloodWaitError as e:
                await asyncio.sleep(e.seconds)
            except Exception as e:
                print(f"❌ Lỗi {target}: {e}")
            
            # Delay giữa các nhóm để tránh bị gậy spam (rất quan trọng)
            await asyncio.sleep(random.randint(90, 150))

        # Nghỉ sau khi đi hết một vòng danh sách nhóm
        await asyncio.sleep(random.randint(300, 600))

# --- CÁC LỆNH ĐIỀU KHIỂN ---
@master_bot.on(events.NewMessage(pattern='/spam'))
async def spam_cmd(event):
    global is_spamming
    if event.sender_id != ADMIN_ID: return
    is_spamming = True
    asyncio.create_task(run_spam_loop())
    await event.reply("🚀 **Đã bắt đầu spam vào danh sách nhóm trong file!**")

@master_bot.on(events.NewMessage(pattern='/stop'))
async def stop_cmd(event):
    global is_spamming
    is_spamming = False
    await event.reply("🛑 **Đã dừng hệ thống.**")

@master_bot.on(events.NewMessage(pattern='/addgroup'))
async def add_g(event):
    if event.sender_id != ADMIN_ID: return
    try:
        group = event.text.split(' ', 1)[1].strip().replace('@', '')
        save_group(group)
        await event.reply(f"✅ Đã thêm nhóm `{group}` vào danh sách spam.")
    except: await event.reply("Nhập: `/addgroup username_nhóm`")

# Các lệnh /start, /status, /setmsg giữ nguyên như bản trước của bạn...

async def main():
    await master_bot.start(bot_token=BOT_TOKEN)
    await master_bot.run_until_disconnected()

if __name__ == "__main__":
    Thread(target=run_web, daemon=True).start()
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
    
