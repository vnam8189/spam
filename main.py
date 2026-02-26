import os, asyncio, random, string
from datetime import datetime
from flask import Flask
from threading import Thread
from telethon import TelegramClient, events, errors, Button
from telethon.tl.functions.messages import SetTypingRequest, SendReactionRequest, MarkContentsAsReadRequest
from telethon.tl.functions.account import UpdateProfileRequest
from telethon.tl.functions.channels import JoinChannelRequest
from telethon.tl.types import SendMessageTypingAction, ReactionEmoji

# --- CẤU HÌNH TỐI CAO ---
API_ID = 36437338 
API_HASH = '18d34c7efc396d277f3db62baa078efc'
BOT_TOKEN = '8499499024:AAFSifEjBAKL2BSmanDDlXuRGh93zvZjM78'
ADMIN_ID = 7816353760 

SESSION_DIR = 'sessions'
if not os.path.exists(SESSION_DIR): os.makedirs(SESSION_DIR)

# --- QUẢN LÝ DỮ LIỆU ---
is_spamming = False
spam_count = 0
last_messages = {}
jail_accounts = set()
blacklist_groups = set()

# NỘI DUNG NÂNG CAO
TEMPLATES = [
    "🤝 Ae chéo link uy tín tại đây, tương tác thực: [Tham gia ngay](https://t.me/xomnguhoc)",
    "🔥 Nhóm chéo link chất nhất, Admin duyệt 24/7: [Vào đây nha](https://t.me/xomnguhoc) 🚀",
    "✅ Group chéo 10k thành viên, uy tín là vàng: [Bấm vào đây](https://t.me/xomnguhoc) ✨"
]

# Sticker/Emoji ngẫu nhiên để giống người
EMOJI_POOL = ["👍", "🔥", "🤩", "🚀", "🤝", "✅", "💎"]

AI_REPLIES = {
    "scam": ["Người thật 100% nha, bot đâu mà bot!", "Đang ngồi trực chéo mỏi tay đây ae 😂", "Hỗ trợ viên nhiệt tình nhất hệ mặt trời đây."],
    "uy tín": ["Nhóm này tui chéo suốt, cực kỳ uy tín.", "Admin làm việc kỹ lắm, yên tâm vào chéo.", "Cứ link đó mà vả, không lo scam."],
    "link": ["Link mình ghim ở trên đó!", "Tham gia ngay group xanh xanh bên trên kìa ae."],
    "ban": ["Hic đừng ban tui, tui chỉ share group tốt cho ae thôi mà.", "Tui đi ngay đây, đừng gắt thế Admin ơi!"]
}

app = Flask('')
@app.route('/')
def home(): return "👑 OVERLORD V16.0 ACTIVE"
def run_web(): app.run(host='0.0.0.0', port=10000)

loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)
master_bot = TelegramClient('master_bot', API_ID, API_HASH)

# --- GIẢ LẬP HÀNH VI CON NGƯỜI (BẢN V16) ---
async def deep_human_simulation(client, target, message):
    try:
        await client(MarkContentsAsReadRequest(peer=target, id=[])) # Đọc tin
        # Giả lập gõ chữ có ngắt quãng (Micro-Breaks)
        parts = [message[i:i+random.randint(5,15)] for i in range(0, len(message), 15)]
        for part in parts:
            async with client.action(target, 'typing'):
                await asyncio.sleep(random.uniform(1.5, 3.5))
        return await client.send_message(target, message, link_preview=False)
    except: return None

# --- GIAO DIỆN ĐIỀU KHIỂN ---
@master_bot.on(events.NewMessage(pattern='/start'))
async def start(event):
    if event.sender_id != ADMIN_ID: return
    text = (
        "👑 **THE ULTIMATE OVERLORD V16.0**\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"📊 **Hệ thống:** `{len(os.listdir(SESSION_DIR))} Quân đoàn`\n"
        f"✉️ **Gửi thành công:** `{spam_count}`\n"
        f"🚫 **Bị chặn:** `{len(jail_accounts)}` | 🏴 **Né nhóm:** `{len(blacklist_groups)}`\n"
        f"⚙️ **Trạng thái:** {'ONLINE 🟢' if is_spamming else 'OFFLINE 🔴'}\n"
        "━━━━━━━━━━━━━━━━━━━━"
    )
    buttons = [
        [Button.inline("🚀 XUẤT QUÂN", b"run"), Button.inline("🛑 THU QUÂN", b"stop")],
        [Button.inline("🎭 CHẠY SEEDING", b"seed"), Button.inline("🧹 CLEAN SYSTEM", b"clean")],
        [Button.inline("🔄 LÀM MỚI CLONE", b"mask")]
    ]
    await event.reply(text, buttons=buttons)

# --- CORE LOGIC (VĂN MINH & AN TOÀN) ---
@master_bot.on(events.CallbackQuery())
async def callback(event):
    global is_spamming
    if event.data == b"run": await event.edit("🎯 Nhập danh sách @nhom1, @nhom2:")
    elif event.data == b"stop": is_spamming = False; await event.edit("🛑 Hệ thống đã ngừng.")

@master_bot.on(events.NewMessage())
async def handle_input(event):
    global is_spamming, spam_count
    if event.sender_id != ADMIN_ID or not event.text.startswith('@'): return
    
    targets = [t.strip() for t in event.text.split(',')]
    sessions = [f for f in os.listdir(SESSION_DIR) if f.endswith('.session')]
    is_spamming = True
    await event.reply("⚔️ **Chế độ Tối Cao đã bật. Quân đoàn đang hành quân...**")

    while is_spamming:
        random.shuffle(targets)
        for target in targets:
            if not is_spamming or target in blacklist_groups: continue
            
            s_file = random.choice([s for s in sessions if s not in jail_accounts])
            c = TelegramClient(os.path.join(SESSION_DIR, s_file), API_ID, API_HASH)
            try:
                await c.connect()
                
                # Tự động Join nếu chưa vào
                try: await c(JoinChannelRequest(target))
                except: pass

                # Xóa tin cũ
                target_ent = await c.get_input_entity(target)
                peer_id = target_ent.channel_id if hasattr(target_ent, 'channel_id') else target
                if s_file in last_messages and peer_id in last_messages[s_file]:
                    try: await c.delete_messages(target, [last_messages[s_file][peer_id]])
                    except: pass

                # Gửi tin nhắn mô phỏng sâu
                msg = random.choice(TEMPLATES) + (" " * random.randint(1, 4))
                sent = await deep_human_simulation(c, target, msg)
                
                if sent:
                    spam_count += 1
                    last_messages[s_file] = {peer_id: sent.id}
                    # Ngẫu nhiên thả emoji dạo
                    if random.random() < 0.3:
                        await c(SendReactionRequest(peer=target, msg_id=sent.id, reaction=[ReactionEmoji(emoticon=random.choice(EMOJI_POOL))]))

            except errors.UserDeactivatedBanError: jail_accounts.add(s_file)
            except: pass
            finally: await c.disconnect()
            
            await asyncio.sleep(random.randint(180, 360)) # Giãn cách siêu an toàn (3-6 phút)
        await asyncio.sleep(random.randint(1200, 2400)) # Nghỉ vòng cực lớn

async def main():
    # Tự động phản hồi (Auto-AI Reply)
    for s_file in [f for f in os.listdir(SESSION_DIR) if f.endswith('.session')]:
        client = TelegramClient(os.path.join(SESSION_DIR, s_file), API_ID, API_HASH)
        @client.on(events.NewMessage(incoming=True))
        async def reply_ai(event):
            if event.is_private: return
            text = event.raw_text.lower()
            # Né Admin: Nếu admin nhắc "ban", "bot", bot sẽ tự im lặng
            for key, val in AI_REPLIES.items():
                if key in text:
                    async with event.client.action(event.chat_id, 'typing'):
                        await asyncio.sleep(random.randint(6, 12))
                        await event.reply(random.choice(val))
        asyncio.create_task(client.start())

    await master_bot.start(bot_token=BOT_TOKEN)
    await master_bot.run_until_disconnected()

if __name__ == "__main__":
    Thread(target=run_web, daemon=True).start()
    loop.run_until_complete(main())
        
