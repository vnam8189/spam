import os
import asyncio
import random
import string
import re
from flask import Flask
from threading import Thread
from telethon import TelegramClient, events, errors
from telethon.tl.functions.channels import JoinChannelRequest

# --- CẤU HÌNH ---
API_ID = 36437338 
API_HASH = '18d34c7efc396d277f3db62baa078efc'
BOT_TOKEN = '8499499024:AAFSifEjBAKL2BSmanDDlXuRGh93zvZjM78'
ADMIN_ID = 7816353760 

SESSION_DIR = 'sessions'
GROUP_FILE = 'groups.txt'

# Tạo thư mục và file cấu hình nếu chưa có
if not os.path.exists(SESSION_DIR): os.makedirs(SESSION_DIR)
if not os.path.exists(GROUP_FILE): open(GROUP_FILE, 'w').close()

# --- KHO NỘI DUNG SPAM ---
MESSAGES_POOL = [
    "Nhóm chéo chất lượng ae vào chéo cùng nhé: {link}",
    "Kèo thơm cho ae cày cuốc, vào nhóm thảo luận: {link}",
    "Group uy tín, không scam, ae vào giao lưu: {link}",
    "Cần tìm đồng đội cùng chí hướng tại: {link}"
]
LINK_NHOM = "t.me/your_group_link" # THAY LINK NHÓM CỦA BẠN VÀO ĐÂY
ICONS = ["🔥", "🚀", "💎", "🧧", "🍀", "✨", "🎯", "⚡", "🌈", "💰"]
is_spamming = False

# --- WEB SERVER (KEEP ALIVE) ---
app = Flask('')
@app.route('/')
def home(): return "🤖 Clone King V7.1 (Render Fixed) is Online!"
def run_web(): app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))

# --- KHỞI TẠO CLIENT ---
master_bot = TelegramClient('master_bot', API_ID, API_HASH)

# --- HÀM HỖ TRỢ ANTI-AI ---
def get_advanced_text():
    base_msg = random.choice(MESSAGES_POOL).format(link=LINK_NHOM)
    # Chèn ký tự ẩn (ZWSP) để lách filter spam của Telegram
    def obfuscate(text):
        return "".join([char + random.choice(['\u200b', '\u200c', '']) for char in text])
    
    icon = random.choice(ICONS)
    return f"{icon} {obfuscate(base_msg)} {icon}"

# --- TÍNH NĂNG AUTO-REPLY ---
active_clients = []

async def start_auto_reply():
    sessions = [f for f in os.listdir(SESSION_DIR) if f.endswith('.session')]
    for s in sessions:
        client = TelegramClient(os.path.join(SESSION_DIR, s), API_ID, API_HASH)
        try:
            await client.connect()
            if await client.is_user_authorized():
                @client.on(events.NewMessage(incoming=True))
                async def handler(event):
                    if not event.is_private:
                        msg_text = event.text.lower()
                        # Kiểm tra từ khóa trong nhóm
                        if "bot" in msg_text or "link" in msg_text:
                            # Nghỉ ngẫu nhiên để giống người thật
                            await asyncio.sleep(random.randint(2, 5))
                            await event.reply(f"Bạn đang tìm link à? Vào đây nhé: {LINK_NHOM}")
                active_clients.append(client)
        except: continue

# --- QUẢN LÝ NHÓM (FILE) ---
def load_groups():
    with open(GROUP_FILE, 'r') as f:
        return [line.strip() for line in f.readlines() if line.strip()]

def save_group(group):
    groups = load_groups()
    if group not in groups:
        with open(GROUP_FILE, 'a') as f:
            f.write(group + '\n')

def remove_group(group):
    groups = load_groups()
    if group in groups:
        groups.remove(group)
        with open(GROUP_FILE, 'w') as f:
            f.write('\n'.join(groups) + '\n')

# --- GIAO DIỆN ĐIỀU KHIỂN (MASTER BOT) ---
@master_bot.on(events.NewMessage(pattern='/start'))
async def start(event):
    if event.sender_id != ADMIN_ID: return
    menu = (
        "👑 **CLONE KING V7.1 - RENDER FIXED**\n"
        "━━━━━━━━━━━━━━━━━━━━━━━\n"
        "📱 **ACC:** `/list`, `/add`, `/delacc [file.session]`\n"
        "👥 **NHÓM:** `/listgroup`, `/addgroup [link]`, `/delgroup [link]`\n"
        "📢 **SPAM:** `/spam` (Tự động rải tin)\n"
        "🤖 **AUTO:** `/autoreply` (Rep khi thấy 'bot')\n"
        "🛑 **DỪNG:** `/stop` | **JOIN:** `/join [link]`"
    )
    await event.reply(menu)

@master_bot.on(events.NewMessage(pattern='/addgroup'))
async def add_group_cmd(event):
    if event.sender_id != ADMIN_ID: return
    try:
        group = event.text.split(' ', 1)[1]
        save_group(group)
        await event.reply(f"✅ Đã thêm nhóm: `{group}`")
    except: await event.reply("⚠️ Nhập: `/addgroup [link/username]`")

@master_bot.on(events.NewMessage(pattern='/listgroup'))
async def list_groups_cmd(event):
    if event.sender_id != ADMIN_ID: return
    groups = load_groups()
    if not groups: return await event.reply("❌ Danh sách nhóm trống.")
    text = "📂 **Danh sách Nhóm:**\n" + "\n".join([f"🔹 `{g}`" for g in groups])
    await event.reply(text)

@master_bot.on(events.NewMessage(pattern='/delgroup'))
async def del_group_cmd(event):
    if event.sender_id != ADMIN_ID: return
    try:
        group = event.text.split(' ', 1)[1]
        remove_group(group)
        await event.reply(f"✅ Đã xóa nhóm: `{group}`")
    except: await event.reply("⚠️ Nhập: `/delgroup [link/username]`")

@master_bot.on(events.NewMessage(pattern='/delacc'))
async def del_acc_cmd(event):
    if event.sender_id != ADMIN_ID: return
    try:
        session_file = event.text.split(' ', 1)[1]
        path = os.path.join(SESSION_DIR, session_file)
        if os.path.exists(path):
            os.remove(path)
            await event.reply(f"✅ Đã xóa acc: `{session_file}`")
        else: await event.reply("❌ Không tìm thấy file session.")
    except: await event.reply("⚠️ Nhập: `/delacc [file.session]`")

@master_bot.on(events.NewMessage(pattern='/autoreply'))
async def autoreply_cmd(event):
    if event.sender_id != ADMIN_ID: return
    await event.reply("⚙️ **Đang khởi động chế độ Auto-Reply...**")
    await start_auto_reply()
    await event.reply(f"✅ Đã kích hoạt {len(active_clients)} acc phản hồi!")

@master_bot.on(events.NewMessage(pattern='/spam'))
async def spam_cmd(event):
    global is_spamming
    if event.sender_id != ADMIN_ID: return
    
    sessions = [f for f in os.listdir(SESSION_DIR) if f.endswith('.session')]
    targets = load_groups()
    
    if not sessions: return await event.reply("❌ Chưa nạp tài khoản!")
    if not targets: return await event.reply("❌ Chưa có nhóm nào! Hãy dùng /addgroup")
    
    is_spamming = True
    await event.reply(f"🚀 **Bắt đầu rải tin...**\n🎯 {len(targets)} nhóm\n👥 {len(sessions)} acc")

    while is_spamming:
        for target in targets:
            if not is_spamming: break
            s_file = random.choice(sessions)
            client = TelegramClient(os.path.join(SESSION_DIR, s_file), API_ID, API_HASH)
            try:
                await client.connect()
                await client.send_message(target, get_advanced_text())
                print(f"Sent to {target} via {s_file}")
            except: pass
            finally: await client.disconnect()
            
            # Giãn cách giữa các nhóm
            await asyncio.sleep(random.randint(40, 60))

        # Nghỉ giữa các vòng
        await asyncio.sleep(random.randint(200, 300))

@master_bot.on(events.NewMessage(pattern='/stop'))
async def stop_cmd(event):
    global is_spamming
    is_spamming = False
    await event.reply("🛑 Đã dừng rải tin.")

# --- QUẢN LÝ TÀI KHOẢN (SESSIONS) ---
@master_bot.on(events.NewMessage(pattern='/list'))
async def list_accs(event):
    if event.sender_id != ADMIN_ID: return
    sessions = [f for f in os.listdir(SESSION_DIR) if f.endswith('.session')]
    if not sessions: return await event.reply("❌ Không có acc.")
    text = "📂 **Danh sách Clone:**\n" + "\n".join([f"🔹 `{s}`" for s in sessions])
    await event.reply(text)

@master_bot.on(events.NewMessage(pattern='/add'))
async def add_account(event):
    if event.sender_id != ADMIN_ID: return
    async with master_bot.conversation(event.chat_id) as conv:
        try:
            await conv.send_message("📞 **Nhập số điện thoại (+84...):**")
            phone = (await conv.get_response()).text.strip()
            s_name = f"{phone.replace('+', '')}.session"
            s_path = os.path.join(SESSION_DIR, s_name)
            client = TelegramClient(s_path, API_ID, API_HASH)
            await client.connect()
            if not await client.is_user_authorized():
                await client.send_code_request(phone)
                await conv.send_message("📩 **Nhập mã OTP:**")
                otp = (await conv.get_response()).text.strip()
                try: 
                    await client.sign_in(phone, otp)
                except errors.SessionPasswordNeededError:
                    await conv.send_message("🔒 **Nhập mật khẩu 2FA:**")
                    await client.sign_in(password=(await conv.get_response()).text.strip())
            await conv.send_message(f"✅ **Đã nạp:** {phone}")
            await client.disconnect()
        except Exception as e: await conv.send_message(f"❌ **Lỗi:** {str(e)}")

@master_bot.on(events.NewMessage())
async def handle_docs(event):
    if event.sender_id != ADMIN_ID or not event.document: return
    if event.document.attributes[0].file_name.endswith('.session'):
        path = await event.download_media(file=SESSION_DIR)
        await event.reply(f"📥 **Đã nhận acc:** `{os.path.basename(path)}`")

@master_bot.on(events.NewMessage(pattern='/join'))
async def join_cmd(event):
    if event.sender_id != ADMIN_ID: return
    try:
        target = event.text.split(' ', 1)[1]
        sessions = [f for f in os.listdir(SESSION_DIR) if f.endswith('.session')]
        await event.reply(f"🔄 **{len(sessions)} clone đang join {target}...**")
        for s in sessions:
            c = TelegramClient(os.path.join(SESSION_DIR, s), API_ID, API_HASH)
            try:
                await c.connect()
                await c(JoinChannelRequest(target))
                await asyncio.sleep(1)
            except: pass
            finally: await c.disconnect()
        await event.reply("✅ **Xong lệnh Join!**")
    except: await event.reply("⚠️ Nhập: `/join [link/username]`")

# --- MAIN ---
async def main():
    await master_bot.start(bot_token=BOT_TOKEN)
    print("Bot đang chạy...")
    await master_bot.run_until_disconnected()

if __name__ == "__main__":
    Thread(target=run_web, daemon=True).start()
    
    # --- ĐOẠN CODE FIX LỖI RUNTIME ERROR TRÊN RENDER ---
    try:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(main())
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(main())
    
