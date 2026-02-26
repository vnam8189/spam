import os, asyncio, random, string, json
from datetime import datetime
from flask import Flask
from threading import Thread
from telethon import TelegramClient, events, errors, Button
from telethon.tl.functions.messages import SetTypingRequest, SendReactionRequest, ReadHistoryRequest
from telethon.tl.functions.account import UpdateProfileRequest
from telethon.tl.functions.channels import JoinChannelRequest
from telethon.tl.types import SendMessageTypingAction, ReactionEmoji

# --- CẤU HÌNH HỆ THỐNG ---
API_ID = 36437338 
API_HASH = '18d34c7efc396d277f3db62baa078efc'
BOT_TOKEN = '8499499024:AAFSifEjBAKL2BSmanDDlXuRGh93zvZjM78'
ADMIN_ID = 7816353760 

SESSION_DIR = 'sessions'
if not os.path.exists(SESSION_DIR): os.makedirs(SESSION_DIR)

# Lưu trữ thông tin tài khoản
ACC_DATA = "accounts_info.json"
if not os.path.exists(ACC_DATA):
    with open(ACC_DATA, 'w') as f: json.dump({}, f)

# --- BIẾN ĐIỀU KHIỂN ---
is_spamming = False
spam_count = 0
LINK_NHOM = "https://t.me/xomnguhoc" # THAY LINK CỦA BẠN VÀO ĐÂY

# --- KỊCH BẢN PHẢN HỒI AI (CHỐT KHÁCH) ---
AI_SCRIPTS = [
    f"Người thật 100% nha ae! Tại nhóm này chéo link uy tín quá nên tui mới share thôi: [Vào đây chéo cực lẹ]({LINK_NHOM}) 🔥",
    f"Bot gì tầm này bác, tui đang ngồi trực chéo mỏi tay đây 😂. Qua đây với tui cho vui: [Tham gia ngay]({LINK_NHOM}) 🤝",
    f"Hic, tui là supporter hỗ trợ ae, thấy ae tìm chỗ chéo sạch nên mới giới thiệu group này: [Link group]({LINK_NHOM}) ✨",
    f"Đang check link cho ae bên này, ai bảo bot là dỗi đó nha! Vào chéo cùng ae cho uy tín: [Bấm vào đây]({LINK_NHOM}) 🚀"
]

TEMPLATES = [
    f"🤝 Chéo link uy tín, tương tác thực tại đây: [Tham gia ngay]({LINK_NHOM})",
    f"🔥 Group chéo link chất nhất 2024, không lo scam: [Vào đây]({LINK_NHOM}) 🚀",
    f"✅ Uy tín là vàng - Chéo nhanh gọn: [Bấm tại đây]({LINK_NHOM}) ✨"
]

# --- QUẢN LÝ WEB ---
app = Flask('')
@app.route('/')
def home(): return "🔱 HYPERION V23.0 IS ACTIVE"
def run_web(): app.run(host='0.0.0.0', port=10000)

master_bot = TelegramClient('master_bot', API_ID, API_HASH)

# --- TIỆN ÍCH ---
def get_acc_info():
    with open(ACC_DATA, 'r') as f: return json.load(f)

def save_acc_info(data):
    with open(ACC_DATA, 'w') as f: json.dump(data, f)

# --- CHỨC NĂNG THÊM ACC QUA TELEGRAM ---
@master_bot.on(events.NewMessage(pattern='/add_acc'))
async def add_acc(event):
    if event.sender_id != ADMIN_ID: return
    async with event.client.conversation(event.chat_id) as conv:
        await conv.send_message("📞 **Nhập số điện thoại (VD: +84123456789):**")
        phone = (await conv.get_response()).text
        client = TelegramClient(os.path.join(SESSION_DIR, phone), API_ID, API_HASH)
        await client.connect()
        try:
            await client.send_code_request(phone)
            await conv.send_message("📩 **Nhập mã xác thực gửi về Telegram:**")
            code = (await conv.get_response()).text
            await client.sign_in(phone, code)
            user = await client.get_me()
            data = get_acc_info()
            data[phone] = {"id": user.id, "name": user.first_name, "status": "active"}
            save_acc_info(data)
            await conv.send_message(f"✅ Đã nạp thành công Chiến binh: **{user.first_name}**")
        except Exception as e:
            await conv.send_message(f"❌ Lỗi: {str(e)}")
        finally: await client.disconnect()

# --- GIAO DIỆN ĐIỀU KHIỂN ---
@master_bot.on(events.NewMessage(pattern='/start'))
async def start(event):
    if event.sender_id != ADMIN_ID: return
    count = len(get_acc_info())
    text = (
        "🔱 **HYPERION COMMAND CENTER V23.0**\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        f"👥 Quân đoàn: `{count} Chiến binh`\n"
        f"✉️ Đã rải: `{spam_count}` tin nhắn\n"
        f"⚙️ Trạng thái: **{'HOẠT ĐỘNG 🟢' if is_spamming else 'NGỪNG 🔴'}**\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        "Gửi danh sách `@nhom1, @nhom2` để bắt đầu."
    )
    buttons = [[Button.inline("🚀 KÍCH HOẠT", b"run"), Button.inline("🛑 DỪNG", b"stop")]]
    await event.reply(text, buttons=buttons)

@master_bot.on(events.CallbackQuery())
async def cb(event):
    global is_spamming
    if event.data == b"run": await event.edit("🎯 Gửi danh sách nhóm mục tiêu:")
    elif event.data == b"stop": is_spamming = False; await event.edit("🛑 Đã dừng.")

# --- CORE LOGIC (VĂN MINH & HIỆU QUẢ) ---
async def human_work(client, target):
    try:
        await client(ReadHistoryRequest(peer=target, max_id=0)) # Đọc tin
        await asyncio.sleep(random.randint(5, 10))
        msg = random.choice(TEMPLATES)
        async with client.action(target, 'typing'):
            await asyncio.sleep(random.randint(5, 12)) # Gõ chữ lâu
            sent = await client.send_message(target, msg, link_preview=False)
            if sent:
                await client(SendReactionRequest(peer=target, msg_id=sent.id, reaction=[ReactionEmoji(emoticon="🔥")]))
                return True
    except: return False

@master_bot.on(events.NewMessage())
async def handle_work(event):
    global is_spamming, spam_count
    if event.sender_id != ADMIN_ID or not event.text.startswith('@'): return
    targets = [t.strip() for t in event.text.split(',')]
    is_spamming = True
    await event.reply("⚔️ **Chiến dịch Hyperion bắt đầu!**")
    while is_spamming:
        data = get_acc_info()
        phones = list(data.keys())
        for target in targets:
            if not is_spamming: break
            phone = random.choice(phones)
            c = TelegramClient(os.path.join(SESSION_DIR, phone), API_ID, API_HASH)
            try:
                await c.connect()
                try: await c(JoinChannelRequest(target))
                except: pass
                if await human_work(c, target): spam_count += 1
            except: pass
            finally: await c.disconnect()
            await asyncio.sleep(random.randint(200, 400))
        await asyncio.sleep(random.randint(900, 1800))

async def main():
    # Khởi động AI phản hồi thông minh cho từng clone
    data = get_acc_info()
    for phone in data:
        client = TelegramClient(os.path.join(SESSION_DIR, phone), API_ID, API_HASH)
        @client.on(events.NewMessage(incoming=True))
        async def reply_handler(event):
            if event.is_private: return
            if "bot" in event.raw_text.lower():
                async with event.client.action(event.chat_id, 'typing'):
                    await asyncio.sleep(random.randint(8, 15))
                    await event.reply(random.choice(AI_SCRIPTS))
        asyncio.create_task(client.start())

    await master_bot.start(bot_token=BOT_TOKEN)
    await master_bot.run_until_disconnected()

if __name__ == "__main__":
    Thread(target=run_web, daemon=True).start()
    loop.run_until_complete(main())
