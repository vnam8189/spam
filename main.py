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
last_messages = {} # Lưu { (session_name, group_username): message_id }
clones = {} # Lưu trữ client đang hoạt động

# --- WEB SERVER ---
app = Flask('')
@app.route('/')
def home(): return "🤖 Bot Clone Safe-Mode V7.5 is Online!"
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

# --- LOGIC PHỤ TRỢ ---
def get_safe_text():
    inv = "".join(random.choices(['\u200b', '\u200c', '\u200d'], k=random.randint(4, 10)))
    icon = random.choice(ICONS)
    return f"{icon} {AD_MESSAGE} {icon}\n{inv}"

# --- MASTER BOT & CLONES ---
master_bot = TelegramClient('master_bot', API_ID, API_HASH)

async def start_reply_handler(client, session_name):
    @client.on(events.NewMessage(incoming=True))
    async def handler(event):
        if event.is_private or not is_spamming: return
        targets = load_groups()
        # Chỉ reply trong những nhóm nằm trong groups.txt
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
                # Xóa tin cũ
                m_key = (s_name, target)
                if m_key in last_messages:
                    try: await client.delete_messages(target, [last_messages[m_key]])
                    except: pass
                
                # Gửi tin mới
                sent = await client.send_message(target, get_safe_text())
                last_messages[m_key] = sent.id
                print(f"✅ {s_name} gửi tới {target}")
            except FloodWaitError as e: await asyncio.sleep(e.seconds)
            except Exception as e: print(f"❌ Lỗi {target}: {e}")
            
            await asyncio.sleep(random.randint(90, 160)) # Delay an toàn

        await asyncio.sleep(random.randint(300, 600))

# --- COMMANDS ---
@master_bot.on(events.NewMessage(pattern='/start'))
async def start(event):
    if event.sender_id != ADMIN_ID: return
    menu = (
        "🛡️ **QUẢN LÝ CLONE V7.5** 🛡️\n"
        "━━━━━━━━━━━━━━━━━━━━━━━\n"
        "📱 **CLONE:** `/add` | `/list` | `/delacc` \n"
        "👥 **NHÓM:** `/addgroup` | `/delgroup` | `/listgroup` \n"
        "🚀 **CHẠY:** `/spam` | `/stop` | `/join` \n"
        "⚙️ **CÀI ĐẶT:** `/setmsg` | `/status` \n"
        "━━━━━━━━━━━━━━━━━━━━━━━"
    )
    await event.reply(menu)

@master_bot.on(events.NewMessage(pattern='/add'))
async def add_account(event):
    if event.sender_id != ADMIN_ID: return
    async with master_bot.conversation(event.chat_id) as conv:
        try:
            await conv.send_message("📞 Nhập số (+84...):")
            phone = (await conv.get_response()).text.strip()
            client = TelegramClient(os.path.join(SESSION_DIR, f"{phone}.session"), API_ID, API_HASH)
            await client.connect()
            if not await client.is_user_authorized():
                await client.send_code_request(phone)
                await conv.send_message("📩 Nhập OTP:")
                otp = (await conv.get_response()).text.strip()
                try: await client.sign_in(phone, otp)
                except SessionPasswordNeededError:
                    await conv.send_message("🔒 Nhập 2FA:")
                    await client.sign_in(password=(await conv.get_response()).text.strip())
            await conv.send_message("✅ Đã thêm acc thành công!")
            await client.disconnect()
        except Exception as e: await conv.send_message(f"❌ Lỗi: {e}")

@master_bot.on(events.NewMessage(pattern='/addgroup'))
async def add_g(event):
    if event.sender_id != ADMIN_ID: return
    try:
        group = event.text.split(' ', 1)[1].strip().replace('@', '')
        save_group(group)
        await event.reply(f"✅ Đã lưu nhóm `{group}`. Dùng `/join` để các clone vào nhóm.")
    except: await event.reply("⚠️ Nhập: `/addgroup username` (không kèm @)")

@master_bot.on(events.NewMessage(pattern='/join'))
async def join_all(event):
    if event.sender_id != ADMIN_ID: return
    targets = load_groups()
    sessions = [f for f in os.listdir(SESSION_DIR) if f.endswith('.session')]
    await event.reply(f"🔄 Đang cho {len(sessions)} clone gia nhập {len(targets)} nhóm...")
    for s in sessions:
        c = TelegramClient(os.path.join(SESSION_DIR, s), API_ID, API_HASH)
        await c.connect()
        for t in targets:
            try: 
                await c(JoinChannelRequest(t))
                await asyncio.sleep(5)
            except: pass
        await c.disconnect()
    await event.reply("✅ Đã hoàn tất lệnh Join!")

@master_bot.on(events.NewMessage(pattern='/spam'))
async def spam_cmd(event):
    global is_spamming
    if event.sender_id != ADMIN_ID: return
    is_spamming = True
    asyncio.create_task(run_spam_loop())
    await event.reply("🚀 **Hệ thống bắt đầu Spam & Auto-Reply!**")

@master_bot.on(events.NewMessage(pattern='/stop'))
async def stop_cmd(event):
    global is_spamming
    is_spamming = False
    await event.reply("🛑 Đã dừng.")

@master_bot.on(events.NewMessage(pattern='/setmsg'))
async def set_msg(event):
    global AD_MESSAGE
    if event.sender_id != ADMIN_ID: return
    AD_MESSAGE = event.text.split('/setmsg ', 1)[1]
    await event.reply("✅ Đã đổi tin nhắn quảng cáo.")

@master_bot.on(events.NewMessage(pattern='/status'))
async def status(event):
    if event.sender_id != ADMIN_ID: return
    sessions = [f for f in os.listdir(SESSION_DIR) if f.endswith('.session')]
    await event.reply(f"📊 Trạng thái: {'Đang chạy 🟢' if is_spamming else 'Dừng 🔴'}\n📱 Clone: {len(sessions)}\n📁 Nhóm: {len(load_groups())}")

async def main():
    await master_bot.start(bot_token=BOT_TOKEN)
    await master_bot.run_until_disconnected()

if __name__ == "__main__":
    Thread(target=run_web, daemon=True).start()
    asyncio.get_event_loop().run_until_complete(main())
                    
