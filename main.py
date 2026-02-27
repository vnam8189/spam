import os, asyncio, random, string, json, sys
from datetime import datetime
from flask import Flask
from threading import Thread
from telethon import TelegramClient, events, errors, Button
from telethon.tl.functions.messages import SetTypingRequest, SendReactionRequest, ReadHistoryRequest
from telethon.tl.functions.account import UpdateProfileRequest, UpdateStatusRequest
from telethon.tl.functions.channels import JoinChannelRequest
from telethon.tl.types import SendMessageTypingAction, ReactionEmoji

# --- CẤU HÌNH ---
API_ID = 36437338 
API_HASH = '18d34c7efc396d277f3db62baa078efc'
BOT_TOKEN = '8499499024:AAFSifEjBAKL2BSmanDDlXuRGh93zvZjM78'
ADMIN_ID = 7816353760 

LINK_NHOM = "https://t.me/xomnguhoc"
SESSION_DIR = 'sessions'
ACC_DATA = "accounts_db.json"

# Danh sách emoji để thả tim dạo (tăng Trust)
REACTIONS = ["👍", "🔥", "❤️", "🤩", "👏"]

# --- HỆ THỐNG QUẢN LÝ ---
stats = {"success": 0, "fail": 0, "jail": 0}
is_spamming = False

def load_db():
    if os.path.exists(ACC_DATA):
        with open(ACC_DATA, 'r') as f: return json.load(f)
    return {}

def save_db(data):
    with open(ACC_DATA, 'w') as f: json.dump(data, f, indent=4)

# --- 🎭 KỊCH BẢN NỘI DUNG BIẾN BIẾN THỂ (Lách Filter) ---
def get_dynamic_template():
    # Thêm ký tự ẩn Unicode vào cuối tin nhắn để mỗi tin nhắn là độc nhất
    hidden_char = "".join(random.choices(['\u200b', '\u200c', '\u200d'], k=random.randint(2, 8)))
    templates = [
        f"🏆 **HỘI AE CHÉO REF - UY TÍN SỐ 1**\n✅ Chéo nhanh - Trả đủ\n👉 [THAM GIA]({LINK_NHOM}) {hidden_char}",
        f"🚀 **CỘNG ĐỒNG CHÉO LINK SIÊU TỐC**\n🔥 Tương tác thực 100%\n👉 [BẤM VÀO ĐÂY]({LINK_NHOM}) {hidden_char}",
        f"✨ **KÈO CHÉO REF SIÊU NGON**\n💎 Uy tín là vàng\n👉 [VÀO NHÓM]({LINK_NHOM}) {hidden_char}"
    ]
    return random.choice(templates)

# --- 🧠 LOGIC GIẢ LẬP NGƯỜI THẬT (ANTI-SCAN) ---
async def simulate_human_action(client, target):
    try:
        # 1. Hiện trạng thái đang xem (Read)
        await client(ReadHistoryRequest(peer=target, max_id=0))
        await asyncio.sleep(random.randint(3, 7))
        
        # 2. Ngẫu nhiên thả tim vào 1 tin nhắn gần nhất trong nhóm để lấy Trust
        if random.random() < 0.5: # 50% cơ hội thực hiện
            messages = await client.get_messages(target, limit=5)
            if messages:
                target_msg = random.choice(messages)
                await client(SendReactionRequest(
                    peer=target, 
                    msg_id=target_msg.id, 
                    reaction=[ReactionEmoji(emoticon=random.choice(REACTIONS))]
                ))
                await asyncio.sleep(random.randint(2, 5))

        # 3. Giả lập gõ chữ với thời gian ngẫu nhiên (Lâu hơn bình thường)
        async with client.action(target, 'typing'):
            typing_time = random.randint(12, 25)
            await asyncio.sleep(typing_time)
            
            # Gửi tin nhắn biến thể
            msg = get_dynamic_template()
            await client.send_message(target, msg, link_preview=False)
            return True
    except:
        return False

# --- 🔱 MASTER CONTROL ---
app = Flask('')
@app.route('/')
def home(): return "🔱 GHOST PROTOCOL ACTIVE"

master_bot = TelegramClient('master_bot', API_ID, API_HASH)

@master_bot.on(events.NewMessage(pattern='/start'))
async def start_handler(event):
    if event.sender_id != ADMIN_ID: return
    db = load_db()
    text = (
        "🔱 **GHOST PROTOCOL V29.0**\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        f"👥 Quân đoàn: `{len(db)} acc` | ✅ OK: `{stats['success']}`\n"
        f"❌ Lỗi: `{stats['fail']}` | 💀 Chết: `{stats['jail']}`\n"
        f"⚙️ Trạng thái: **{'RUNNING' if is_spamming else 'IDLE'}**\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        "Gửi danh sách `@nhom1, @nhom2` để xuất kích."
    )
    buttons = [[Button.inline("🚀 CHẠY", b"run"), Button.inline("🛑 DỪNG", b"stop")]]
    await event.reply(text, buttons=buttons)

@master_bot.on(events.CallbackQuery())
async def cb(event):
    global is_spamming
    if event.data == b"run": await event.edit("🎯 Nhập danh sách nhóm mục tiêu:")
    elif event.data == b"stop": is_spamming = False; await event.edit("🛑 Đã thu quân.")

@master_bot.on(events.NewMessage())
async def handle_input(event):
    global is_spamming, stats
    if event.sender_id != ADMIN_ID or not event.text.startswith('@'): return
    
    targets = [t.strip() for t in event.text.split(',')]
    db = load_db()
    phones = [p for p in db if db[p]['status'] == 'alive']
    
    if not phones: return await event.reply("❌ Không có acc nào. Dùng `/add_acc` để nạp.")
    
    is_spamming = True
    await event.reply(f"⚔️ **GIAO THỨC BÓNG MA KHỞI CHẠY!**\nSử dụng {len(phones)} acc rải quân...")

    while is_spamming:
        random.shuffle(targets)
        for target in targets:
            if not is_spamming: break
            
            phone = random.choice(phones)
            # Khởi tạo client với Device Model ngẫu nhiên để lách quét thiết bị
            c = TelegramClient(os.path.join(SESSION_DIR, phone), API_ID, API_HASH, 
                               device_model=f"iPhone {random.randint(12,15)} Pro",
                               system_version="17.4.1")
            try:
                await c.connect()
                if not await c.is_user_authorized():
                    db[phone]['status'] = 'died'; save_db(db)
                    stats["jail"] += 1; continue
                
                try: await c(JoinChannelRequest(target))
                except: pass
                
                if await simulate_human_action(c, target):
                    stats["success"] += 1
                else:
                    stats["fail"] += 1
                
            except Exception: stats["fail"] += 1
            finally: await c.disconnect()
            
            # GIÃN CÁCH CỰC QUAN TRỌNG: Nghỉ 5-10 phút để tránh bị đánh dấu Spam
            await asyncio.sleep(random.randint(300, 600))
        
        # Nghỉ dài sau mỗi vòng (15-30 phút)
        await master_bot.send_message(ADMIN_ID, f"📊 **BÁO CÁO:** Thành công: {stats['success']} | Lỗi: {stats['fail']}")
        await asyncio.sleep(random.randint(900, 1800))

# (Giữ nguyên logic /add_acc từ bản trước để nạp acc live qua OTP)
# ... [Logic nạp acc đã có ở bản V28.0] ...

async def main():
    await master_bot.start(bot_token=BOT_TOKEN)
    await master_bot.run_until_disconnected()

if __name__ == "__main__":
    Thread(target=lambda: app.run(host='0.0.0.0', port=10000), daemon=True).start()
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(main())
    
