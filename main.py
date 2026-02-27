import os, asyncio, random, json, re
from flask import Flask, render_template_string
from threading import Thread
from telethon import TelegramClient, events, Button
from telethon.tl.functions.messages import ReadHistoryRequest

# ==========================================
# 🛠️ CONFIGURATION
# ==========================================
class Config:
    API_ID = 36437338 
    API_HASH = '18d34c7efc396d277f3db62baa078efc'
    BOT_TOKEN = '8499499024:AAFSifEjBAKL2BSmanDDlXuRGh93zvZjM78'
    ADMIN_ID = 7816353760 
    LINK_NHOM = "https://t.me/xomnguhoc"
    SESSION_DIR = 'sessions'
    DB_FILE = "prestige_v41.json"
    MIN_DELAY = 60 # Giảm delay để spam nhanh hơn, spin-tax lo việc anti-ban
    MAX_DELAY = 120

class Database:
    @staticmethod
    def load():
        if os.path.exists(Config.DB_FILE):
            try:
                with open(Config.DB_FILE, 'r') as f: return json.load(f)
            except: pass
        return {"accounts": {}, "stats": {"success": 0, "fail": 0, "banned": 0}, "running": False}
    
    @staticmethod
    def save(data):
        with open(Config.DB_FILE, 'w') as f: json.dump(data, f, indent=4)

# ==========================================
# 🧠 AI BRAIN
# ==========================================
class PrestigeBrain:
    @staticmethod
    def get_spin(text):
        return re.sub(r'\{(.*?)\}', lambda m: random.choice(m.group(1).split('|')), text)

    @staticmethod
    def stealth(text):
        # Chèn ký tự tàng hình
        chars = ['\u200b', '\u200c', '\u200d']
        return " ".join([w + random.choice(chars) for w in text.split(' ')])

    @staticmethod
    def get_random_qc():
        # 15 mẫu khác nhau
        samples = [
            "{🚀 HỘI CHÉO REF UY TÍN|🔥 KÈO CHÉO REF NHANH}\n{✅ Trả link 100%|✅ Không bao giờ bùng}\n👉 [THAM GIA]({link})",
            "{💎 Tham gia ngay để cùng tăng ref|👉 Nhóm chéo chất lượng nhất Telegram}\n{✅ Trả link ngay sau 5s|🔥 Uy tín|💎 Seeding}\n👉 Link: {link}",
            "{🔥 Kèo thơm cho ae chéo ref|🚀 Hội chéo ref uy tín}\n{🚫 Scam - Bùng link|✅ Trả link nhanh}\n👉 [JOIN]({link})",
            "{✅ Trả link 100% - Không bao giờ bùng|✅ Trả link nhanh}\n{🚀 HỘI CHÉO REF UY TÍN|💎 Seeding nhóm}\n👉 [THAM GIA]({link})",
            "{🔥 Kèo thơm|🚀 Hội chéo ref uy tín|💎 Tham gia ngay}\n{✅ Trả link nhanh|🚫 Nói không với scam}\n👉 Link: {link}",
            "{🚀 Hội chéo ref uy tín|🔥 Kèo chéo ref nhanh}\n{✅ Trả link 100%|✅ Không bao giờ bùng}\n👉 [THAM GIA]({link})",
            "{✅ Trả link nhanh|🚫 Nói không với scam}\n{🔥 Kèo thơm|🚀 Hội chéo ref uy tín|💎 Tham gia ngay}\n👉 [JOIN]({link})",
            "{💎 Seeding nhóm|🚀 Hội chéo ref uy tín}\n{✅ Trả link 100%|✅ Không bao giờ bùng}\n👉 Link: {link}",
            "{🚫 Nói không với scam|✅ Trả link nhanh}\n{🔥 Kèo thơm|🚀 Hội chéo ref uy tín|💎 Tham gia ngay}\n👉 [JOIN]({link})",
            "{🚀 Hội chéo ref uy tín|🔥 Kèo chéo ref nhanh}\n{✅ Trả link 100%|✅ Không bao giờ bùng}\n👉 [THAM GIA]({link})",
            "{🔥 Siêu kèo chéo|🚀 Chéo ref chất}\n{✅ Trả link nhanh|💎 Uy tín}\n👉 [THAM GIA]({link})",
            "{💎 Hội chéo ref|🔥 Kèo chất}\n{🚫 Scam - Bùng link|✅ Trả link 100%}\n👉 Link: {link}",
            "{🚀 Chéo ref uy tín|🔥 Kèo ref nhanh}\n{✅ Không bùng|💎 Trả link ngay}\n👉 [JOIN]({link})",
            "{🔥 Kèo chéo ref uy tín|🚀 Hội chéo ref nhanh}\n{✅ Trả link 100%|🚫 Scam}\n👉 [THAM GIA]({link})",
            "{✅ Trả link ngay|🔥 Siêu kèo ref}\n{🚀 Hội chéo ref|💎 Seeding}\n👉 Link: {link}"
        ]
        text = random.choice(samples)
        return PrestigeBrain.stealth(PrestigeBrain.get_spin(text).format(link=Config.LINK_NHOM))

# ==========================================
# ⚡ CORE LOGIC
# ==========================================
class CoreLogic:
    @staticmethod
    async def spam(phone, target):
        client = TelegramClient(os.path.join(Config.SESSION_DIR, phone), Config.API_ID, Config.API_HASH)
        try:
            await client.connect()
            if not await client.is_user_authorized(): return False
            await client(ReadHistoryRequest(peer=target, max_id=0))
            await asyncio.sleep(random.randint(2, 5))
            async with client.action(target, 'typing'):
                await asyncio.sleep(random.randint(3, 6))
                await client.send_message(target, PrestigeBrain.get_random_qc(), link_preview=False)
                return True
        except: return False
        finally: await client.disconnect()

    @staticmethod
    async def auto_reply(event):
        if event.is_private or not event.sender or not event.sender.username: return
        text = event.raw_text.lower()
        if "bot" in text:
            reply = f"🤔 @{event.sender.username} Lại nói bot? Nhóm chéo uy tín 100%!\n\n"
            reply += PrestigeBrain.get_random_qc()
            await asyncio.sleep(random.randint(1, 3))
            await event.reply(PrestigeBrain.stealth(reply))

# ==========================================
# 🌐 UI & DASHBOARD (NEON STYLE)
# ==========================================
app = Flask('')
@app.route('/')
def ui():
    data = Database.load()
    s = data["stats"]
    accs = data["accounts"]
    return render_template_string("""
    <!DOCTYPE html>
    <html>
    <head>
        <title>PRESTIGE V41.0</title>
        <style>
            body { background-color: #0a0a0a; color: #00ff9d; font-family: 'Courier New', monospace; padding: 20px; }
            h1 { color: #fff; text-shadow: 0 0 10px #00ff9d; }
            .card { border: 2px solid #00ff9d; border-radius: 10px; padding: 15px; margin-bottom: 20px; background: #111; box-shadow: 0 0 15px #00ff9d; }
            .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 15px; }
            .stats-box { text-align: center; font-size: 1.2em; font-weight: bold; }
        </style>
    </head>
    <body>
        <h1>PRESTIGE V41.0 - DASHBOARD</h1>
        <div class="card">
            <h2>Hệ thống</h2>
            <p>Trạng thái: {{ "⚡ ĐANG CHẠY" if data.running else "💤 ĐANG NGHỈ" }}</p>
            <div class="grid stats-box">
                <div>✅ THÀNH CÔNG<br>{{s.success}}</div>
                <div>⚠️ LỖI<br>{{s.fail}}</div>
                <div>❌ BAN<br>{{s.banned}}</div>
                <div>📱 TÀI KHOẢN<br>{{accs|length}}</div>
            </div>
        </div>
        <div class="card">
            <h2>Tài khoản hoạt động</h2>
            <ul>
            {% for phone, status in accs.items() %}
                <li>{{phone}} - <span style="color: {{ '#0f0' if status == 'active' else '#f00' }}">{{status}}</span></li>
            {% endfor %}
            </ul>
        </div>
    </body>
    </html>
    """, data=data, s=s, accs=accs)

# ==========================================
# 📡 MASTER BOT
# ==========================================
master = TelegramClient('master_bot', Config.API_ID, Config.API_HASH)

@master.on(events.NewMessage(pattern='/start'))
async def master_ui(event):
    if event.sender_id != Config.ADMIN_ID: return
    btns = [[Button.inline("🚀 CHẠY", b"run"), Button.inline("🛑 DỪNG", b"stop")]]
    await event.reply("🔱 **Prestige V41.0**\n⚡ Giao diện đã nâng cấp.", buttons=btns)

@master.on(events.CallbackQuery())
async def cb(event):
    data = Database.load()
    if event.data == b"run":
        data["running"] = True
        Database.save(data)
        await event.edit("🎯 Gửi list nhóm (phẩy):")
    elif event.data == b"stop":
        data["running"] = False
        Database.save(data)
        await event.edit("🛑 Stopped.")

@master.on(events.NewMessage(pattern='/add'))
async def add_acc(event):
    if event.sender_id != Config.ADMIN_ID: return
    async with event.client.conversation(event.chat_id) as conv:
        await conv.send_message("📱 SĐT:")
        phone = (await conv.get_response()).text.strip()
        client = TelegramClient(os.path.join(Config.SESSION_DIR, phone), Config.API_ID, Config.API_HASH)
        await client.connect()
        try:
            await client.send_code_request(phone)
            await conv.send_message("📩 OTP:")
            await client.sign_in(phone, (await conv.get_response()).text.strip())
            data = Database.load()
            data["accounts"][phone] = "active"
            Database.save(data)
            await conv.send_message("✅ Thêm OK!")
        except Exception as e: await conv.send_message(f"Lỗi: {e}")

# ==========================================
# 🚀 RUNNER
# ==========================================
@master.on(events.NewMessage())
async def run_mission(event):
    if event.sender_id != Config.ADMIN_ID or not event.text.startswith('@'): return
    targets = [t.strip() for t in event.text.split(',')]
    data = Database.load()
    data["running"] = True
    Database.save(data)

    while data["running"]:
        data = Database.load()
        active_accs = [p for p in data["accounts"] if data["accounts"][p] == 'active']
        if not active_accs: break
        for target in targets:
            data = Database.load()
            if not data["running"]: break
            await CoreLogic.spam(random.choice(active_accs), target)
            await asyncio.sleep(random.randint(Config.MIN_DELAY, Config.MAX_DELAY))

async def boot():
    if not os.path.exists(Config.SESSION_DIR): os.makedirs(Config.SESSION_DIR)
    await master.start(bot_token=Config.BOT_TOKEN)
    data = Database.load()
    for phone in data["accounts"]:
        c = TelegramClient(os.path.join(Config.SESSION_DIR, phone), Config.API_ID, Config.API_HASH)
        c.add_event_handler(CoreLogic.auto_reply, events.NewMessage(incoming=True))
        try: await c.start()
        except: pass
    await master.run_until_disconnected()

if __name__ == "__main__":
    Thread(target=lambda: app.run(host='0.0.0.0', port=10000), daemon=True).start()
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(boot())
    
