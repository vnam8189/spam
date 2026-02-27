import os, asyncio, random, string, json, sys, logging
from datetime import datetime
from flask import Flask
from threading import Thread
from telethon import TelegramClient, events, errors, Button
from telethon.tl.functions.messages import SetTypingRequest, SendReactionRequest, ReadHistoryRequest, GetHistoryRequest
from telethon.tl.functions.account import UpdateProfileRequest, UpdateStatusRequest
from telethon.tl.functions.channels import JoinChannelRequest, GetFullChannelRequest, GetParticipantRequest
from telethon.tl.types import SendMessageTypingAction, ReactionEmoji, UserStatusOnline, ChannelParticipantBanned

# --- CẤU HÌNH TỐI CAO ---
API_ID = 36437338 
API_HASH = '18d34c7efc396d277f3db62baa078efc'
BOT_TOKEN = '8499499024:AAFSifEjBAKL2BSmanDDlXuRGh93zvZjM78'
ADMIN_ID = 7816353760 
LINK_NHOM = "https://t.me/xomnguhoc"

SESSION_DIR = 'sessions'
ACC_DATA = "accounts_v30.json"
LOG_FILE = "system.log"

# Tạo môi trường
for d in [SESSION_DIR]: 
    if not os.path.exists(d): os.makedirs(d)

# --- DATABASE ENGINE ---
class Database:
    @staticmethod
    def load():
        if os.path.exists(ACC_DATA):
            with open(ACC_DATA, 'r') as f: return json.load(f)
        return {}
    @staticmethod
    def save(data):
        with open(ACC_DATA, 'w') as f: json.dump(data, f, indent=4)

stats = {"ok": 0, "fail": 0, "banned": 0, "total_sent": 0}
is_running = False

# --- KỊCH BẢN AI CHỐT KHÁCH (GEN Z STYLE) ---
AI_DEFENSE = [
    "Bot cái gì, tui đang ngồi trực chéo mỏi cả tay đây ông nội 😂 qua đây mà xem: {link}",
    "Người thật chéo thật nha, nhóm này admin duyệt tay nên sạch lắm ae: {link}",
    "Hic, tui hỗ trợ ae chéo link uy tín mà bảo tui bot là dỗi á! Vào thử đi: {link}",
    "Vừa chéo xong bên này, lẹ lắm ae, đừng nghe mấy ông kia nói bot: {link}",
    "Chỗ này bao uy tín, tui chơi mấy tháng nay rồi, ae vào mà vả: {link}"
]

SPAM_TEMPLATES = [
    "🏆 **HỘI AE CHÉO REF - TRẢ ĐỦ 100%**\n━━━━━━━━━━━━━━━━━━━━\n🔥 Duyệt link siêu tốc\n🔥 Không scam - Không kick\n👉 [THAM GIA NGAY]({link})",
    "🚀 **CỘNG ĐỒNG CHÉO LINK BÁ ĐẠO 2026**\n━━━━━━━━━━━━━━━━━━━━\n✅ Tương tác thực từ ae\n✅ Admin hỗ trợ 24/7\n👉 [BẤM VÀO ĐÂY]({link})"
]

# --- GIẢ LẬP THIẾT BỊ (ANTI-BAN) ---
DEVICES = [
    {"model": "iPhone 15 Pro Max", "ver": "17.4.1"},
    {"model": "Samsung Galaxy S24 Ultra", "ver": "14.0"},
    {"model": "Google Pixel 8 Pro", "ver": "14.0"},
    {"model": "Xiaomi 14 Ultra", "ver": "13.0"}
]

# --- LOGIC NGƯỜI THẬT (THE GHOST) ---
async def perform_human_behavior(client, target):
    try:
        # 1. Giả vờ cuộn tin nhắn để đọc nội dung cũ
        offset_id = 0
        for _ in range(random.randint(1, 3)):
            history = await client(GetHistoryRequest(
                peer=target, offset_id=offset_id, offset_date=None,
                add_offset=0, limit=10, max_id=0, min_id=0, hash=0
            ))
            if not history.messages: break
            offset_id = history.messages[-1].id
            await asyncio.sleep(random.randint(2, 5))

        # 2. Thả tim ngẫu nhiên vào tin nhắn gần nhất
        if random.random() < 0.6:
            messages = await client.get_messages(target, limit=3)
            if messages:
                await client(SendReactionRequest(
                    peer=target, msg_id=random.choice(messages).id,
                    reaction=[ReactionEmoji(emoticon=random.choice(["🔥", "👍", "❤️"]))]
                ))
                await asyncio.sleep(random.randint(3, 6))

        # 3. Giả lập gõ chữ (Vừa gõ vừa dừng)
        async with client.action(target, 'typing'):
            await asyncio.sleep(random.randint(15, 30))
            msg = random.choice(SPAM_TEMPLATES).format(link=LINK_NHOM)
            # Thêm ký tự ẩn để mỗi tin nhắn là duy nhất
            msg += "".join(random.choices(['\u200b', '\u200c'], k=5))
            await client.send_message(target, msg, link_preview=False)
            return True
    except Exception as e:
        print(f"[-] Lỗi hành vi: {e}")
        return False

# --- HỆ THỐNG NẠP ACC (OTP LIVE) ---
master_bot = TelegramClient('master_bot', API_ID, API_HASH)

@master_bot.on(events.NewMessage(pattern='/add_acc'))
async def add_acc_logic(event):
    if event.sender_id != ADMIN_ID: return
    async with event.client.conversation(event.chat_id) as conv:
        await conv.send_message("📱 **NHẬP SỐ ĐIỆN THOẠI (VD: +84...):**")
        phone = (await conv.get_response()).text.strip()
        
        device = random.choice(DEVICES)
        client = TelegramClient(os.path.join(SESSION_DIR, phone), API_ID, API_HASH,
                                device_model=device['model'], system_version=device['ver'])
        await client.connect()
        
        try:
            await client.send_code_request(phone)
            await conv.send_message("📩 **NHẬP MÃ OTP (5 CHỮ SỐ):**")
            otp = (await conv.get_response()).text.strip()
            await client.sign_in(phone, otp)
        except errors.SessionPasswordNeededError:
            await conv.send_message("🔐 **NHẬP MẬT KHẨU 2 LỚP (2FA):**")
            pwd = (await conv.get_response()).text.strip()
            await client.sign_in(password=pwd)
        except Exception as e:
            await conv.send_message(f"❌ Lỗi: {e}")
            return
            
        me = await client.get_me()
        db = Database.load()
        db[phone] = {"id": me.id, "name": me.first_name, "status": "alive", "device": device['model']}
        Database.save(db)
        await conv.send_message(f"✅ Đã nạp thành công: **{me.first_name}**")
        await client.disconnect()

# --- DASHBOARD ĐIỀU KHIỂN ---
@master_bot.on(events.NewMessage(pattern='/start'))
async def dashboard(event):
    if event.sender_id != ADMIN_ID: return
    db = Database.load()
    alive = len([p for p in db if db[p]['status'] == 'alive'])
    text = (
        f"🔱 **APOCALYPSE V30.0 - DASHBOARD**\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"💂 Quân đoàn: `{alive}/{len(db)}` Acc hoạt động\n"
        f"✅ Đã rải: `{stats['total_sent']}` | 💀 Chết: `{stats['banned']}`\n"
        f"⚙️ Trạng thái: **{'⚡️ ĐANG XUẤT KÍCH' if is_running else '💤 ĐANG NGHỈ'}**\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"Hãy gửi danh sách `@nhom1, @nhom2` để tấn công!"
    )
    buttons = [[Button.inline("🚀 KÍCH HOẠT", b"run"), Button.inline("🛑 DỪNG QUÂN", b"stop")]]
    await event.reply(text, buttons=buttons)

@master_bot.on(events.CallbackQuery())
async def cb_handler(event):
    global is_running
    if event.data == b"run": await event.edit("🎯 **Nhập danh sách cụm nhóm mục tiêu:**")
    elif event.data == b"stop": is_running = False; await event.edit("🛑 **Hệ thống đang thu quân...**")

@master_bot.on(events.NewMessage())
async def handle_mission(event):
    global is_running, stats
    if event.sender_id != ADMIN_ID or not event.text.startswith('@'): return
    
    targets = [t.strip() for t in event.text.split(',')]
    is_running = True
    await event.reply(f"⚔️ **CHIẾN DỊCH BẮT ĐẦU!**\nĐang triển khai quân đội đến {len(targets)} mặt trận...")

    while is_running:
        db = Database.load()
        phones = [p for p in db if db[p]['status'] == 'alive']
        if not phones: break

        for target in targets:
            if not is_running: break
            
            phone = random.choice(phones)
            client = TelegramClient(os.path.join(SESSION_DIR, phone), API_ID, API_HASH)
            try:
                await client.connect()
                if not await client.is_user_authorized():
                    db[phone]['status'] = 'died'; Database.save(db); stats['banned'] += 1; continue
                
                # Tham gia nhóm (Nếu chưa vào)
                try: await client(JoinChannelRequest(target))
                except: pass
                
                # Thực thi chuỗi hành động "Ghost"
                if await perform_human_behavior(client, target):
                    stats['total_sent'] += 1
                else: stats['fail'] += 1
                
            except Exception: stats['fail'] += 1
            finally: await client.disconnect()
            
            # GIÃN CÁCH TRÁNH QUÉT: Nghỉ 5-12 phút mỗi lần gửi
            await asyncio.sleep(random.randint(300, 700))
        
        # Báo cáo kết quả vòng quét
        await master_bot.send_message(ADMIN_ID, f"📊 **BÁO CÁO CHIẾN TRƯỜNG:**\n✅ Thành công: {stats['total_sent']}\n💀 Acc bị ban: {stats['banned']}")
        await asyncio.sleep(random.randint(1200, 2400))

# --- KHỞI CHẠY ---
app = Flask('')
@app.route('/')
def h(): return "V30.0 ACTIVE"

async def system_init():
    # Tự động khởi chạy AI Phản hồi cho tất cả acc đang sống
    db = Database.load()
    for phone in db:
        if db[phone]['status'] == 'alive':
            c = TelegramClient(os.path.join(SESSION_DIR, phone), API_ID, API_HASH)
            @c.on(events.NewMessage(incoming=True))
            async def ai_brain(event):
                if event.is_private: return
                if any(x in event.raw_text.lower() for x in ["bot", "scam", "lừa"]):
                    async with event.client.action(event.chat_id, 'typing'):
                        await asyncio.sleep(random.randint(5, 10))
                        await event.reply(random.choice(AI_DEFENSE).format(link=LINK_NHOM))
            try: await c.start()
            except: pass

    await master_bot.start(bot_token=BOT_TOKEN)
    await master_bot.run_until_disconnected()

if __name__ == "__main__":
    Thread(target=lambda: app.run(host='0.0.0.0', port=10000), daemon=True).start()
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(system_init())
            
