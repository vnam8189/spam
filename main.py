import os, asyncio, random, string, json
from datetime import datetime
from flask import Flask
from threading import Thread
from telethon import TelegramClient, events, errors, Button
from telethon.tl.functions.messages import SetTypingRequest, SendReactionRequest, ReadHistoryRequest
from telethon.tl.functions.account import UpdateProfileRequest, UpdateStatusRequest
from telethon.tl.functions.channels import JoinChannelRequest
from telethon.tl.types import SendMessageTypingAction, ReactionEmoji, UserStatusOnline, UserStatusOffline

# --- CẤU HÌNH ---
API_ID = 36437338 
API_HASH = '18d34c7efc396d277f3db62baa078efc'
BOT_TOKEN = '8499499024:AAFSifEjBAKL2BSmanDDlXuRGh93zvZjM78'
ADMIN_ID = 7816353760 

SESSION_DIR = 'sessions'
if not os.path.exists(SESSION_DIR): os.makedirs(SESSION_DIR)

ACC_DATA = "accounts_info.json"
if not os.path.exists(ACC_DATA):
    with open(ACC_DATA, 'w') as f: json.dump({}, f)

is_spamming = False
spam_count = 0
LINK_NHOM = "https://t.me/xomnguhoc" # THAY LINK THẬT CỦA BẠN

# Kịch bản AI "Chốt khách"
AI_SCRIPTS = [
    f"Bot gì ae, tui đang trực chéo mỏi tay đây này 😂. Qua đây với tui: [Vào Group]({LINK_NHOM}) 🔥",
    f"Người thật việc thật nha, thấy ae cần chỗ uy tín nên tui share group này: [Tham gia ngay]({LINK_NHOM}) 🤝",
    f"Hic, tui hỗ trợ ae chéo link thôi, ai bảo bot là tui dỗi đó! Vào đây mà xem: [Link]({LINK_NHOM}) 🚀",
    f"Đang check link cho ae muốn xỉu đây, vào đây chéo với tui cho lẹ: [Group Uy Tín]({LINK_NHOM}) 💎"
]

TEMPLATES = [
    f"🤝 Chéo link uy tín, tương tác thật 100%: [Tham gia ngay]({LINK_NHOM})",
    f"🔥 Group chéo link đông nhất, không lo bị kick: [Vào đây]({LINK_NHOM}) 🚀",
    f"✅ Uy tín là vàng - Chéo nhanh gọn lẹ: [Bấm tại đây]({LINK_NHOM}) ✨"
]

app = Flask('')
@app.route('/')
def home(): return "🔱 ECLIPSE V24.0 IS RUNNING"
def run_web(): app.run(host='0.0.0.0', port=10000)

master_bot = TelegramClient('master_bot', API_ID, API_HASH)

def get_acc_info():
    with open(ACC_DATA, 'r') as f: return json.load(f)

def save_acc_info(data):
    with open(ACC_DATA, 'w') as f: json.dump(data, f)

# --- CHỨC NĂNG THÊM ACC QUA BOT ---
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
            await conv.send_message(f"✅ Đã nạp Chiến binh: **{user.first_name}**")
        except Exception as e: await conv.send_message(f"❌ Lỗi: {str(e)}")
        finally: await client.disconnect()

@master_bot.on(events.NewMessage(pattern='/start'))
async def start(event):
    if event.sender_id != ADMIN_ID: return
    count = len(get_acc_info())
    text = (
        "🔱 **THE ECLIPSE V24.0**\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        f"👥 Quân đoàn: `{count} acc` | ✉️ Đã gửi: `{spam_count}`\n"
        f"⚙️ Trạng thái: **{'ONLINE 🟢' if is_spamming else 'OFFLINE 🔴'}**\n"
        "━━━━━━━━━━━━━━━━━━━━━"
    )
    buttons = [[Button.inline("🚀 KÍCH HOẠT", b"run"), Button.inline("🛑 DỪNG", b"stop")]]
    await event.reply(text, buttons=buttons)

@master_bot.on(events.CallbackQuery())
async def cb(event):
    global is_spamming
    if event.data == b"run": await event.edit("🎯 Gửi danh sách nhóm (VD: `@nhom1, @nhom2`):")
    elif event.data == b"stop": is_spamming = False; await event.edit("🛑 Đã thu quân.")

async def human_work(client, target):
    try:
        await client(UpdateStatusRequest(offline=False)) # Hiện Online
        await client(ReadHistoryRequest(peer=target, max_id=0))
        await asyncio.sleep(random.randint(5, 10))
        msg = random.choice(TEMPLATES) + "".join(random.choices(['\u200b', '\u200c'], k=5))
        async with client.action(target, 'typing'):
            await asyncio.sleep(random.randint(6, 15))
            sent = await client.send_message(target, msg, link_preview=False)
            if sent:
                await client(SendReactionRequest(peer=target, msg_id=sent.id, reaction=[ReactionEmoji(emoticon="🔥")]))
        await client(UpdateStatusRequest(offline=True)) # Hiện Offline
        return True
    except: return False

@master_bot.on(events.NewMessage())
async def handle_work(event):
    global is_spamming, spam_count
    if event.sender_id != ADMIN_ID or not event.text.startswith('@'): return
    targets = [t.strip() for t in event.text.split(',')]
    is_spamming = True
    await event.reply("⚔️ **Chiến dịch Eclipse khởi động! Dàn quân đang xuất kích...**")
    while is_spamming:
        data = get_acc_info()
        phones = list(data.keys())
        if not phones: break
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
            await asyncio.sleep(random.randint(180, 350))
        await asyncio.sleep(random.randint(1000, 2000))

async def main_logic():
    # Khởi động AI phản hồi cho từng clone
    data = get_acc_info()
    for phone in data:
        client = TelegramClient(os.path.join(SESSION_DIR, phone), API_ID, API_HASH)
        @client.on(events.NewMessage(incoming=True))
        async def reply_ai(event):
            if event.is_private: return
            text = event.raw_text.lower()
            if any(k in text for k in ["bot", "lừa", "uy tín", "link"]):
                async with event.client.action(event.chat_id, 'typing'):
                    await asyncio.sleep(random.randint(8, 15))
                    await event.reply(random.choice(AI_SCRIPTS))
        asyncio.create_task(client.start())

    await master_bot.start(bot_token=BOT_TOKEN)
    await master_bot.run_until_disconnected()

if __name__ == "__main__":
    Thread(target=run_web, daemon=True).start()
    # Fix lỗi loop name error
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(main_logic())
