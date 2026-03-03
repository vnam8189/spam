import os
import asyncio
import random
from flask import Flask
from threading import Thread
from telethon import TelegramClient, events, errors
from telethon.tl.functions.channels import JoinChannelRequest
from telethon.errors import FloodWaitError, SessionPasswordNeededError

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
last_messages = {} # { (session, group): message_id }
clones = {} 

# --- WEB SERVER (RENDER ALIVE) ---
app = Flask('')
@app.route('/')
def home(): return "🤖 Bot Clone Safe-Mode V8.0 is Online!"

def run_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

# --- QUẢN LÝ DỮ LIỆU ---
def load_groups():
    if not os.path.exists(GROUP_FILE): return []
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
    inv = "".join(random.choices(['\u200b', '\u200c', '\u200d'], k=random.randint(4, 10)))
    icon = random.choice(ICONS)
    return f"{icon} {AD_MESSAGE} {icon}\n{inv}"

# --- LOGIC CLONE (SPAM & REPLY) ---
master_bot = TelegramClient('master_bot', API_ID, API_HASH)

async def start_reply_handler(client, session_name):
    @client.on(events.NewMessage(incoming=True))
    async def handler(event):
        if event.is_private or not is_spamming: return
        targets = load_groups()
        is_target = False
        if event.chat:
            username = getattr(event.chat, 'username', None)
            if username and any(username in g for g in targets): is_target = True
        
        if is_target and any(word in (event.text or "").lower() for word in KEYWORDS_REPLY):
            await asyncio.sleep(random.randint(3, 8))
            try: await event.reply(f"🤖 {AD_MESSAGE}")
            except: pass

async def run_spam_loop():
    global is_spamming, last_messages
    while is_spamming:
        targets = load_groups()
        session_files = [f for f in os.listdir(SESSION_DIR) if f.endswith('.session')]
        
        if not targets or not session_files:
            await asyncio.sleep(20)
            continue

        for target in targets:
            if not is_spamming: break
            s_name = random.choice(session_files)
            
            if s_name not in clones:
                c = TelegramClient(os.path.join(SESSION_DIR, s_name), API_ID, API_HASH)
                try:
                    await c.connect()
                    if await c.is_user_authorized():
                        await start_reply_handler(c, s_name)
                        clones[s_name] = c
                    else: continue
                except: continue
            
            client = clones[s_name]
            try:
                # 1. Xóa tin cũ
                m_key = (s_name, target)
                if m_key in last_messages:
                    try: await client.delete_messages(target, [last_messages[m_key]])
                    except: pass
                
                # 2. Gửi tin mới
                sent = await client.send_message(target, get_safe_text())
                last_messages[m_key] = sent.id
                print(f"✅ {s_name} đã gửi tin tới {target}")
            except FloodWaitError as e:
                await asyncio.sleep(e.seconds)
            except Exception as e:
                print(f"❌ Lỗi tại {target}: {e}")
            
            await asyncio.sleep(random.randint(90, 160))

        await asyncio.sleep(random.randint(300, 600))

# --- COMMANDS ---
@master_bot.on(events.NewMessage(pattern='/start'))
async def start(event):
    if event.sender_id != ADMIN_ID: return
    menu = (
        "🛡️ **HỆ THỐNG CLONE V8.0 - RENDER MODE** 🛡️\n"
        "━━━━━━━━━━━━━━━━━━━━━━━\n"
        "📱 **ACC:** `/add` | `/list` | `/delacc` \n"
        "👥 **NHÓM:** `/addgroup` | `/delgroup` | `/listgroup` \n"
        "🚀 **CHẠY:** `/spam` | `/stop` | `/join` \n"
        "⚙️ **HỆ THỐNG:** `/setmsg` | `/status` \n"
        "━━━━━━━━━━━━━━━━━━━━━━━\n"
        "💡 *Tip: Bạn có thể gửi file .session trực tiếp vào đây để nạp nhanh!*"
    )
    await event.reply(menu)

@master_bot.on(events.NewMessage(pattern='/add'))
async def add_account(event):
    if event.sender_id != ADMIN_ID: return
    async with master_bot.conversation(event.chat_id) as conv:
        try:
            await conv.send_message("📞 Nhập số điện thoại (+84...):")
            phone = (await conv.get_response()).text.strip()
            client = TelegramClient(os.path.join(SESSION_DIR, f"{phone}.session"), API_ID, API_HASH)
            await client.connect()
            if not await client.is_user_authorized():
                await client.send_code_request(phone)
                await conv.send_message("📩 Nhập mã OTP:")
                otp = (await conv.get_response()).text.strip()
                try: await client.sign_in(phone, otp)
                except SessionPasswordNeededError:
                    await conv.send_message("🔒 Nhập mật khẩu 2FA:")
                    await client.sign_in(password=(await conv.get_response()).text.strip())
            await conv.send_message(f"✅ Đã nạp thành công: {phone}")
            await client.disconnect()
        except Exception as e: await conv.send_message(f"❌ Lỗi: {str(e)}")

@master_bot.on(events.NewMessage(pattern='/addgroup'))
async def add_g(event):
    if event.sender_id != ADMIN_ID: return
    try:
        group = event.text.split(' ', 1)[1].strip().replace('@', '').replace('https://t.me/', '')
        save_group(group)
        await event.reply(f"✅ Đã thêm nhóm: `{group}`")
    except: await event.reply("⚠️ Nhập: `/addgroup username`")

@master_bot.on(events.NewMessage(pattern='/spam'))
async def spam_cmd(event):
    global is_spamming
    if event.sender_id != ADMIN_ID: return
    if is_spamming: return await event.reply("✅ Hệ thống đang chạy rồi!")
    is_spamming = True
    asyncio.create_task(run_spam_loop())
    await event.reply("🚀 **Bắt đầu Spam & Auto-Reply...**")

@master_bot.on(events.NewMessage(pattern='/stop'))
async def stop_cmd(event):
    global is_spamming
    is_spamming = False
    await event.reply("🛑 Đã dừng hệ thống.")

@master_bot.on(events.NewMessage(pattern='/status'))
async def status(event):
    if event.sender_id != ADMIN_ID: return
    sessions = [f for f in os.listdir(SESSION_DIR) if f.endswith('.session')]
    groups = load_groups()
    stt = "🟢 Đang chạy" if is_spamming else "🔴 Đang nghỉ"
    await event.reply(f"📊 **Trạng thái:** {stt}\n📱 **Số acc:** {len(sessions)}\n📁 **Số nhóm:** {len(groups)}")

@master_bot.on(events.NewMessage())
async def handle_session_file(event):
    if event.sender_id != ADMIN_ID or not event.document: return
    if event.document.attributes[0].file_name.endswith('.session'):
        await event.download_media(file=SESSION_DIR)
        await event.reply(f"📥 Đã nhận file session thành công!")

# --- KHỞI CHẠY ---
async def start_all():
    await master_bot.start(bot_token=BOT_TOKEN)
    print("🤖 BOT ĐÃ ONLINE!")
    await master_bot.run_until_disconnected()

if __name__ == "__main__":
    # Chạy Web Server để Render không tắt bot
    Thread(target=run_web, daemon=True).start()
    
    # Chạy Bot
    loop = asyncio.get_event_loop()
    loop.run_until_complete(start_all())
        
