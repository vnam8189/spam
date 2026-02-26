import os, asyncio, random, string
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

# --- BIẾN QUẢN LÝ ---
is_spamming = False
spam_count = 0
last_messages = {}
jail_accounts = set()

# --- KỊCH BẢN MARKETING & PHẢN HỒI AI ---
# Thay link group của bạn vào đây
LINK_NHOM = "https://t.me/xomnguhoc"

TEMPLATES = [
    f"🤝 Ae chéo link uy tín tại đây, tương tác thực: [Tham gia ngay]({LINK_NHOM})",
    f"🔥 Nhóm chéo link chất nhất, Admin duyệt 24/7: [Vào đây nha]({LINK_NHOM}) 🚀",
    f"✅ Group chéo 10k thành viên, uy tín là vàng: [Bấm vào đây]({LINK_NHOM}) ✨"
]

# Kịch bản khi bị gọi là "bot" - Vừa cãi vừa chốt khách
AI_BOT_REDIRECT = [
    f"Bot gì tầm này ae, tại nhóm này chéo link nhanh quá nên tui mới share cho ae thôi: [Vào đây chéo cực lẹ]({LINK_NHOM}) 🔥",
    f"Người thật 100% nha! Thấy ae tìm chỗ chéo uy tín nên tui mới giới thiệu group này: [Tham gia ngay]({LINK_NHOM}) 🤝",
    f"Hic, tui là supporter bên nhóm này, thấy ae nhiệt nên mời qua đây chéo cho an toàn: [Bấm vào đây]({LINK_NHOM}) ✨",
    f"Đang ngồi check link cho ae mỏi tay đây, bot đâu mà bot. Qua đây chéo với tui: [Link nhóm]({LINK_NHOM}) 💎",
    f"Bot mà biết chỗ nào chéo link uy tín như này thì tui cũng chịu đó 😂 Vào xem đi: [Vào đây]({LINK_NHOM}) 🚀"
]

app = Flask('')
@app.route('/')
def home(): return "🔱 ETERNAL OVERLORD V20.0 ACTIVE"
def run_web(): app.run(host='0.0.0.0', port=10000)

loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)
master_bot = TelegramClient('master_bot', API_ID, API_HASH)

# --- GIẢ LẬP HÀNH VI CON NGƯỜI SIÊU CẤP ---
async def human_emulation(client, target, message=None):
    try:
        # Đọc tin nhắn cũ để lấy Trust
        await client(ReadHistoryRequest(peer=target, max_id=0))
        await asyncio.sleep(random.randint(3, 7))
        
        if message:
            async with client.action(target, 'typing'):
                # Gõ chữ có nhịp nghỉ ngẫu nhiên
                for _ in range(random.randint(2, 4)):
                    await asyncio.sleep(random.uniform(1.5, 3.0))
                return await client.send_message(target, message, link_preview=False)
    except: return None

# --- GIAO DIỆN COMMAND CENTER ---
@master_bot.on(events.NewMessage(pattern='/start'))
async def start(event):
    if event.sender_id != ADMIN_ID: return
    sessions = [f for f in os.listdir(SESSION_DIR) if f.endswith('.session')]
    text = (
        "🔱 **ETERNAL OVERLORD V20.0**\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"👥 Quân đoàn: `{len(sessions)} acc`\n"
        f"✉️ Tổng tin đã gửi: `{spam_count}`\n"
        f"🚫 Acc bị hạn chế: `{len(jail_accounts)}`\n"
        f"⚙️ Trạng thái: **{'RUNNING 🟢' if is_spamming else 'STOPPED 🔴'}**\n"
        "━━━━━━━━━━━━━━━━━━━━"
    )
    buttons = [
        [Button.inline("🚀 KÍCH HOẠT CHIẾN DỊCH", b"run"), Button.inline("🛑 THU QUÂN", b"stop")],
        [Button.inline("🔄 LÀM MỚI CLONE", b"mask"), Button.inline("🧹 DỌN DẤU VẾT", b"clean")]
    ]
    await event.reply(text, buttons=buttons)

@master_bot.on(events.CallbackQuery())
async def callback(event):
    global is_spamming
    if event.data == b"run":
        await event.edit("🎯 Gửi danh sách nhóm mục tiêu (VD: `@nhom1, @nhom2`):")
    elif event.data == b"stop":
        is_spamming = False
        await event.edit("🛑 Đã dừng hệ thống. Dàn clone tàng hình thành công.")

# --- CORE LOGIC (MASTERMIND) ---
@master_bot.on(events.NewMessage())
async def handle_input(event):
    global is_spamming, spam_count
    if event.sender_id != ADMIN_ID or not event.text.startswith('@'): return
    
    targets = [t.strip() for t in event.text.split(',')]
    sessions = [f for f in os.listdir(SESSION_DIR) if f.endswith('.session')]
    is_spamming = True
    await event.reply("⚔️ **Chiến dịch V20.0 bắt đầu. Dàn quân đang thâm nhập...**")

    while is_spamming:
        random.shuffle(targets)
        for target in targets:
            if not is_spamming: break
            
            active_accs = [s for s in sessions if s not in jail_accounts]
            if not active_accs: break
            
            s_file = random.choice(active_accs)
            c = TelegramClient(os.path.join(SESSION_DIR, s_file), API_ID, API_HASH)
            try:
                await c.connect()
                
                # Tham gia nhóm & dọn tin cũ
                try: await c(JoinChannelRequest(target))
                except: pass
                
                target_ent = await c.get_input_entity(target)
                peer_id = target_ent.channel_id if hasattr(target_ent, 'channel_id') else target
                if s_file in last_messages and peer_id in last_messages[s_file]:
                    try: await c.delete_messages(target, [last_messages[s_file][peer_id]])
                    except: pass

                # Spam như người thật
                msg = random.choice(TEMPLATES) + (" " * random.randint(1, 3))
                sent = await human_emulation(c, target, msg)
                
                if sent:
                    spam_count += 1
                    last_messages[s_file] = {peer_id: sent.id}
                    # Tự reaction để tăng độ nổi bật
                    try: await c(SendReactionRequest(peer=target, msg_id=sent.id, reaction=[ReactionEmoji(emoticon="🔥")]))
                    except: pass

            except errors.UserDeactivatedBanError: jail_accounts.add(s_file)
            except: pass
            finally: await c.disconnect()
            
            await asyncio.sleep(random.randint(180, 300)) # Nghỉ an toàn
        await asyncio.sleep(random.randint(900, 1800)) # Nghỉ vòng lớn

async def main():
    # Khởi động AI phản hồi thông minh cho từng clone
    for s_file in [f for f in os.listdir(SESSION_DIR) if f.endswith('.session')]:
        client = TelegramClient(os.path.join(SESSION_DIR, s_file), API_ID, API_HASH)
        @client.on(events.NewMessage(incoming=True))
        async def reply_handler(event):
            if event.is_private: return
            if "bot" in event.raw_text.lower():
                async with event.client.action(event.chat_id, 'typing'):
                    await asyncio.sleep(random.randint(7, 13))
                    await event.reply(random.choice(AI_BOT_REDIRECT))
        asyncio.create_task(client.start())

    await master_bot.start(bot_token=BOT_TOKEN)
    await master_bot.run_until_disconnected()

if __name__ == "__main__":
    Thread(target=run_web, daemon=True).start()
    loop.run_until_complete(main())
    
