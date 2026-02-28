import os
import asyncio
import random
import string
from flask import Flask
from threading import Thread
from telethon import TelegramClient, events, errors
from telethon.tl.functions.channels import JoinChannelRequest
from telethon.tl.types import Channel

# --- CẤU HÌNH ---
API_ID = 36437338 
API_HASH = '18d34c7efc396d277f3db62baa078efc'
BOT_TOKEN = '8499499024:AAFSifEjBAKL2BSmanDDlXuRGh93zvZjM78'
ADMIN_ID = 7816353760 

SESSION_DIR = 'sessions'
if not os.path.exists(SESSION_DIR): os.makedirs(SESSION_DIR)

# Nội dung mặc định
AD_MESSAGE = "Nhóm chéo chất lượng ae vào chéo đi : Tham gia ngay (Link nhóm)"
ICONS = ["🔥", "🚀", "💎", "🧧", "🍀", "✨", "🎯", "⚡", "🌈", "💰"]
is_spamming = False

# --- WEB SERVER (KEEP ALIVE) ---
app = Flask('')
@app.route('/')
def home(): return "🤖 Bot Clone Safe-Mode is Online!"
def run_web(): app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))

# --- KHỞI TẠO EVENT LOOP ---
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)
master_bot = TelegramClient('master_bot', API_ID, API_HASH)

# --- CHỨC NĂNG ANTI-SPAM ---
def get_safe_text():
    # Chèn ký tự ẩn ngẫu nhiên để lách AI của Telegram
    invisible = "".join(random.choices(['\u200b', '\u200c', '\u200d'], k=random.randint(3, 6)))
    icon = random.choice(ICONS)
    # Đã bỏ mã bảo mật
    return f"{icon} {AD_MESSAGE} {icon}\n{invisible}"

# --- CHỨC NĂNG TỰ ĐỘNG TRẢ LỜI ---
async def reply_to_bot_keyword(client):
    @client.on(events.NewMessage(incoming=True))
    async def handler(event):
        if not event.is_private and event.text:
            if "bot" in event.text.lower():
                await asyncio.sleep(random.randint(1, 3)) # Trễ ngẫu nhiên để giống người thật
                await event.reply(f"🤖 **Bạn nhắc tới bot à?**\n{AD_MESSAGE}")

# --- QUẢN LÝ TÀI KHOẢN CLONE ---
async def start_clones():
    sessions = [f for f in os.listdir(SESSION_DIR) if f.endswith('.session')]
    for s_file in sessions:
        client = TelegramClient(os.path.join(SESSION_DIR, s_file), API_ID, API_HASH)
        await client.connect()
        if await client.is_user_authorized():
            await reply_to_bot_keyword(client)
            # Không dùng client.disconnect() ở đây để duy trì kết nối lắng nghe

# --- GIAO DIỆN MENU ---
@master_bot.on(events.NewMessage(pattern='/start'))
async def start(event):
    if event.sender_id != ADMIN_ID: return
    menu = (
        "🛡️ **HỆ THỐNG CLONE SIÊU GIÃN CÁCH V5.1** 🛡️\n"
        "━━━━━━━━━━━━━━━━━━━━━━━\n"
        "📱 **QUẢN LÝ ACC:**\n"
        "├ `/add` : Nạp số (Nhập OTP trực tiếp)\n"
        "├ `/list` : Xem danh sách Clone hiện có\n"
        "└ *Gửi file .session* để nạp nhanh\n\n"
        "📢 **QUẢNG CÁO:**\n"
        "├ `/setmsg [nội dung]` : Đổi tin nhắn\n"
        "├ `/join @nhom1, @nhom2` : Vào nhiều nhóm\n"
        "└ `/spam @nhom1, @nhom2` : Rải tin (1p/lần)\n\n"
        "⚙️ **HỆ THỐNG:**\n"
        "├ `/stop` : Dừng rải tin ngay lập tức\n"
        "└ `/status` : Kiểm tra tiến độ\n"
        "━━━━━━━━━━━━━━━━━━━━━━━\n"
        "🕒 *Cơ chế: Nghỉ 60s giữa nhóm - 5p giữa vòng*"
    )
    await event.reply(menu)

@master_bot.on(events.NewMessage(pattern='/status'))
async def status(event):
    if event.sender_id != ADMIN_ID: return
    sessions = [f for f in os.listdir(SESSION_DIR) if f.endswith('.session')]
    stt = "Đang chạy 🟢" if is_spamming else "Đang nghỉ 🔴"
    await event.reply(f"📊 **Trạng thái:** {stt}\n👥 **Số acc:** {len(sessions)} clone")

@master_bot.on(events.NewMessage(pattern='/list'))
async def list_accs(event):
    if event.sender_id != ADMIN_ID: return
    sessions = [f for f in os.listdir(SESSION_DIR) if f.endswith('.session')]
    if not sessions: return await event.reply("❌ Không có acc nào.")
    text = "📂 **Danh sách Clone:**\n" + "\n".join([f"🔹 `{s}`" for s in sessions])
    await event.reply(text)

@master_bot.on(events.NewMessage(pattern='/setmsg'))
async def set_msg(event):
    global AD_MESSAGE
    if event.sender_id != ADMIN_ID: return
    try:
        AD_MESSAGE = event.text.split('/setmsg ', 1)[1]
        await event.reply(f"✅ **Đã cập nhật nội dung:**\n{AD_MESSAGE}")
    except: await event.reply("⚠️ Nhập: `/setmsg [nội dung]`")

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
            # Khởi động lại các client để cập nhật acc mới
            await start_clones()
        except Exception as e: await conv.send_message(f"❌ **Lỗi:** {str(e)}")

@master_bot.on(events.NewMessage(pattern='/spam'))
async def spam_cmd(event):
    global is_spamming
    if event.sender_id != ADMIN_ID: return
    try:
        targets = [t.strip() for t in event.text.split('/spam ', 1)[1].split(',')]
        sessions = [f for f in os.listdir(SESSION_DIR) if f.endswith('.session')]
        if not sessions: return await event.reply("❌ Chưa nạp tài khoản clone!")
        
        is_spamming = True
        await event.reply(f"🚀 **Đang rải tin Siêu Giãn Cách (1p/lần) vào {len(targets)} nhóm...**")

        while is_spamming:
            random.shuffle(targets)
            for target in targets:
                if not is_spamming: break
                s_file = random.choice(sessions)
                client = TelegramClient(os.path.join(SESSION_DIR, s_file), API_ID, API_HASH)
                try:
                    await client.connect()
                    await client.send_message(target, get_safe_text())
                except: pass
                finally: await client.disconnect()
                
                # Nghỉ ~1 phút giữa các nhóm
                if is_spamming:
                    await asyncio.sleep(random.randint(55, 70))

            # Nghỉ lớn ~5 phút giữa các vòng
            if is_spamming:
                await asyncio.sleep(random.randint(300, 450))
    except: await event.reply("⚠️ Nhập: `/spam @nhom1, @nhom2`")

@master_bot.on(events.NewMessage(pattern='/stop'))
async def stop_cmd(event):
    global is_spamming
    is_spamming = False
    await event.reply("🛑 **Hệ thống đã dừng gửi tin.**")

@master_bot.on(events.NewMessage())
async def handle_docs(event):
    if event.sender_id != ADMIN_ID or not event.document: return
    if event.document.attributes[0].file_name.endswith('.session'):
        path = await event.download_media(file=SESSION_DIR)
        await event.reply(f"📥 **Đã nhận acc:** `{os.path.basename(path)}`")
        await start_clones() # Khởi động lại acc mới

@master_bot.on(events.NewMessage(pattern='/join'))
async def join_cmd(event):
    if event.sender_id != ADMIN_ID: return
    try:
        targets = [t.strip() for t in event.text.split('/join ', 1)[1].split(',')]
        sessions = [f for f in os.listdir(SESSION_DIR) if f.endswith('.session')]
        await event.reply(f"🔄 **Cho {len(sessions)} clone join {len(targets)} nhóm...**")
        for target in targets:
            for s in sessions:
                c = TelegramClient(os.path.join(SESSION_DIR, s), API_ID, API_HASH)
                try:
                    await c.connect()
                    await c(JoinChannelRequest(target))
                    await asyncio.sleep(2)
                except: pass
                finally: await c.disconnect()
        await event.reply("✅ **Xong lệnh Join!**")
    except: pass

async def main():
    await master_bot.start(bot_token=BOT_TOKEN)
    await start_clones() # Khởi chạy chức năng tự trả lời
    await master_bot.run_until_disconnected()

if __name__ == "__main__":
    Thread(target=run_web, daemon=True).start()
    loop.run_until_complete(main())
        
