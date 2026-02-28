import os
import asyncio
import random
import string
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

if not os.path.exists(SESSION_DIR): os.makedirs(SESSION_DIR)
if not os.path.exists(GROUP_FILE): open(GROUP_FILE, 'w').close()

# Nội dung mặc định
AD_MESSAGE = "Nhóm chéo chất lượng ae vào chéo đi : Tham gia ngay (Link nhóm)"
ICONS = ["🔥", "🚀", "💎", "🧧", "🍀", "✨", "🎯", "⚡", "🌈", "💰"]
is_spamming = False

# --- WEB SERVER (KEEP ALIVE) ---
app = Flask('')
@app.route('/')
def home(): return "🤖 Bot Clone Safe-Mode V6.0 is Online!"
def run_web(): app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))

# --- KHỞI TẠO EVENT LOOP ---
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)
master_bot = TelegramClient('master_bot', API_ID, API_HASH)

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

# --- CHỨC NĂNG ANTI-SPAM ---
def get_safe_text():
    invisible = "".join(random.choices(['\u200b', '\u200c', '\u200d'], k=random.randint(3, 6)))
    icon = random.choice(ICONS)
    return f"{icon} {AD_MESSAGE} {icon}\n{invisible}"

# --- CHỨC NĂNG TỰ ĐỘNG TRẢ LỜI ---
async def reply_to_bot_keyword(client):
    @client.on(events.NewMessage(incoming=True))
    async def handler(event):
        if not event.is_private and event.text:
            if "bot" in event.text.lower():
                await asyncio.sleep(random.randint(1, 3)) 
                await event.reply(f"🤖 **Bạn nhắc tới bot à?**\n{AD_MESSAGE}")

# --- QUẢN LÝ TÀI KHOẢN CLONE ---
async def start_clones():
    sessions = [f for f in os.listdir(SESSION_DIR) if f.endswith('.session')]
    for s_file in sessions:
        client = TelegramClient(os.path.join(SESSION_DIR, s_file), API_ID, API_HASH)
        try:
            await client.connect()
            if await client.is_user_authorized():
                await reply_to_bot_keyword(client)
        except:
            pass # Bỏ qua nếu acc lỗi

# --- GIAO DIỆN MENU ---
@master_bot.on(events.NewMessage(pattern='/start'))
async def start(event):
    if event.sender_id != ADMIN_ID: return
    menu = (
        "🛡️ **HỆ THỐNG CLONE V6.0 - QUẢN LÝ PRO** 🛡️\n"
        "━━━━━━━━━━━━━━━━━━━━━━━\n"
        "📱 **QUẢN LÝ ACC:**\n"
        "├ `/add` : Nạp số (Nhập OTP)\n"
        "├ `/list` : Xem danh sách Clone\n"
        "└ `/delacc [file.session]` : Xóa acc lỗi\n\n"
        "👥 **QUẢN LÝ NHÓM:**\n"
        "├ `/addgroup [link]` : Thêm nhóm vào danh sách\n"
        "├ `/delgroup [link]` : Xóa nhóm khỏi danh sách\n"
        "└ `/listgroup` : Xem danh sách nhóm đã lưu\n\n"
        "📢 **QUẢNG CÁO & AUTO:**\n"
        "├ `/setmsg [nội dung]` : Đổi tin nhắn\n"
        "├ `/join` : Cho clone join tất cả nhóm đã lưu\n"
        "└ `/spam` : Bắt đầu rải tin vào danh sách nhóm\n\n"
        "⚙️ **HỆ THỐNG:**\n"
        "├ `/stop` : Dừng rải tin\n"
        "└ `/status` : Kiểm tra trạng thái\n"
        "━━━━━━━━━━━━━━━━━━━━━━━"
    )
    await event.reply(menu)

# --- CÁC LỆNH QUẢN LÝ NHÓM ---
@master_bot.on(events.NewMessage(pattern='/addgroup'))
async def add_group_cmd(event):
    if event.sender_id != ADMIN_ID: return
    try:
        group = event.text.split(' ', 1)[1].strip()
        save_group(group)
        await event.reply(f"✅ Đã thêm nhóm: `{group}`")
    except: await event.reply("⚠️ Nhập: `/addgroup [link/username]`")

@master_bot.on(events.NewMessage(pattern='/delgroup'))
async def del_group_cmd(event):
    if event.sender_id != ADMIN_ID: return
    try:
        group = event.text.split(' ', 1)[1].strip()
        remove_group(group)
        await event.reply(f"✅ Đã xóa nhóm: `{group}`")
    except: await event.reply("⚠️ Nhập: `/delgroup [link/username]`")

@master_bot.on(events.NewMessage(pattern='/listgroup'))
async def list_groups_cmd(event):
    if event.sender_id != ADMIN_ID: return
    groups = load_groups()
    if not groups: return await event.reply("❌ Danh sách nhóm trống.")
    text = "📂 **Danh sách Nhóm:**\n" + "\n".join([f"🔹 `{g}`" for g in groups])
    await event.reply(text)

# --- CÁC LỆNH QUẢN LÝ ACC ---
@master_bot.on(events.NewMessage(pattern='/delacc'))
async def del_acc_cmd(event):
    if event.sender_id != ADMIN_ID: return
    try:
        session_file = event.text.split(' ', 1)[1].strip()
        path = os.path.join(SESSION_DIR, session_file)
        if os.path.exists(path):
            os.remove(path)
            await event.reply(f"✅ Đã xóa acc: `{session_file}`")
        else: await event.reply("❌ Không tìm thấy file session.")
    except: await event.reply("⚠️ Nhập: `/delacc [file.session]`")

@master_bot.on(events.NewMessage(pattern='/list'))
async def list_accs(event):
    if event.sender_id != ADMIN_ID: return
    sessions = [f for f in os.listdir(SESSION_DIR) if f.endswith('.session')]
    if not sessions: return await event.reply("❌ Không có acc nào.")
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
            await conv.send_message(f"✅ **Đã nạp thành công:** {phone}")
            await client.disconnect()
            await start_clones()
        except Exception as e: await conv.send_message(f"❌ **Lỗi:** {str(e)}")

# --- CÁC LỆNH HOẠT ĐỘNG ---
@master_bot.on(events.NewMessage(pattern='/spam'))
async def spam_cmd(event):
    global is_spamming
    if event.sender_id != ADMIN_ID: return
    
    targets = load_groups()
    sessions = [f for f in os.listdir(SESSION_DIR) if f.endswith('.session')]
    
    if not sessions: return await event.reply("❌ Chưa nạp tài khoản clone!")
    if not targets: return await event.reply("❌ Danh sách nhóm trống! Dùng /addgroup")
    
    is_spamming = True
    await event.reply(f"🚀 **Đang rải tin vào {len(targets)} nhóm...**")

    while is_spamming:
        random.shuffle(targets)
        for target in targets:
            if not is_spamming: break
            s_file = random.choice(sessions)
            client = TelegramClient(os.path.join(SESSION_DIR, s_file), API_ID, API_HASH)
            try:
                await client.connect()
                await client.send_message(target, get_safe_text())
            except Exception as e:
                print(f"Lỗi gửi tin {target} bằng {s_file}: {e}")
            finally: 
                if client.is_connected():
                    await client.disconnect()
            
            if is_spamming: await asyncio.sleep(random.randint(55, 70))

        if is_spamming: await asyncio.sleep(random.randint(300, 450))

@master_bot.on(events.NewMessage(pattern='/join'))
async def join_cmd(event):
    if event.sender_id != ADMIN_ID: return
    targets = load_groups()
    sessions = [f for f in os.listdir(SESSION_DIR) if f.endswith('.session')]
    
    if not sessions or not targets:
        return await event.reply("❌ Thiếu acc hoặc danh sách nhóm trống.")

    await event.reply(f"🔄 **Cho {len(sessions)} clone join {len(targets)} nhóm...**")
    for target in targets:
        for s in sessions:
            c = TelegramClient(os.path.join(SESSION_DIR, s), API_ID, API_HASH)
            try:
                await c.connect()
                await c(JoinChannelRequest(target))
                await asyncio.sleep(2)
            except Exception as e: 
                print(f"Lỗi join {target} bằng {s}: {e}")
            finally: 
                if c.is_connected():
                    await c.disconnect()
    await event.reply("✅ **Xong lệnh Join!**")

@master_bot.on(events.NewMessage(pattern='/stop'))
async def stop_cmd(event):
    global is_spamming
    is_spamming = False
    await event.reply("🛑 **Hệ thống đã dừng gửi tin.**")

@master_bot.on(events.NewMessage(pattern='/status'))
async def status(event):
    if event.sender_id != ADMIN_ID: return
    sessions = [f for f in os.listdir(SESSION_DIR) if f.endswith('.session')]
    groups = load_groups()
    stt = "Đang chạy 🟢" if is_spamming else "Đang nghỉ 🔴"
    await event.reply(f"📊 **Trạng thái:** {stt}\n👥 **Số acc:** {len(sessions)}\n📁 **Số nhóm:** {len(groups)}")

@master_bot.on(events.NewMessage(pattern='/setmsg'))
async def set_msg(event):
    global AD_MESSAGE
    if event.sender_id != ADMIN_ID: return
    try:
        AD_MESSAGE = event.text.split('/setmsg ', 1)[1]
        await event.reply(f"✅ **Đã cập nhật nội dung:**\n{AD_MESSAGE}")
    except: await event.reply("⚠️ Nhập: `/setmsg [nội dung]`")

@master_bot.on(events.NewMessage())
async def handle_docs(event):
    if event.sender_id != ADMIN_ID or not event.document: return
    if event.document.attributes[0].file_name.endswith('.session'):
        path = await event.download_media(file=SESSION_DIR)
        await event.reply(f"📥 **Đã nhận acc:** `{os.path.basename(path)}`")
        await start_clones()

async def main():
    await master_bot.start(bot_token=BOT_TOKEN)
    await start_clones() 
    await master_bot.run_until_disconnected()

if __name__ == "__main__":
    Thread(target=run_web, daemon=True).start()
    try:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(main())
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(main())
                
