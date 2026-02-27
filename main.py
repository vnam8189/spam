import os, asyncio, random, json, re
from flask import Flask, render_template_string
from threading import Thread
from telethon import TelegramClient, events, errors, Button
from telethon.tl.functions.messages import ReadHistoryRequest
from telethon.tl.types import ReactionEmoji

# ==========================================
# 🛰️ CORE SYSTEM ARCHITECTURE
# ==========================================

class Config:
    API_ID = 36437338 
    API_HASH = '18d34c7efc396d277f3db62baa078efc'
    BOT_TOKEN = '8499499024:AAFSifEjBAKL2BSmanDDlXuRGh93zvZjM78'
    ADMIN_ID = 7816353760 
    LINK_NHOM = "https://t.me/xomnguhoc"
    SESSION_DIR = 'sessions'
    DB_FILE = "synthetic_v34.json"
    INTERVAL = 120 # Chu kỳ 2 phút spam

class Logger:
    logs = []
    @classmethod
    def add(cls, msg, type="info"):
        t = __import__('datetime').datetime.now().strftime("%H:%M:%S")
        cls.logs.append({"time": t, "msg": msg, "type": type})
        if len(cls.logs) > 20: cls.logs.pop(0)

class Database:
    @staticmethod
    def load():
        if os.path.exists(Config.DB_FILE):
            with open(Config.DB_FILE, 'r') as f: return json.load(f)
        return {}
    @staticmethod
    def save(data):
        with open(Config.DB_FILE, 'w') as f: json.dump(data, f, indent=4)

# ==========================================
# 🧠 AI ENGINE: HUMAN SIMULATION
# ==========================================

class HumanBrain:
    @staticmethod
    def get_spintax(text):
        def rep(m): return random.choice(m.group(1).split('|'))
        return re.sub(r'\{(.*?)\}', rep, text)

    @staticmethod
    def apply_invisible_hash(text):
        chars = ['\u200b', '\u200c', '\u200d']
        words = text.split(' ')
        new_text = ""
        for w in words:
            new_text += w + random.choice(chars) + " "
        return new_text.strip()

# ==========================================
# 🔱 OMNI CONTROL: DASHBOARD & MASTER
# ==========================================

app = Flask('')
state = {"success": 0, "fail": 0, "banned": 0, "is_running": False}

@app.route('/')
def ui():
    return render_template_string("""
    <!DOCTYPE html>
    <style>
        body { background: #000; color: #0f0; font-family: 'Consolas', monospace; padding: 20px; }
        .grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 15px; }
        .card { border: 1px solid #0f0; padding: 15px; box-shadow: 0 0 10px #0f0; text-align: center; }
        .log { background: #111; border: 1px solid #333; height: 350px; margin-top: 20px; padding: 10px; overflow-y: scroll; }
        .info { color: #00d4ff; } .warn { color: #ffae00; } .error { color: #ff0055; }
        h1 { text-transform: uppercase; letter-spacing: 5px; text-shadow: 0 0 20px #0f0; }
    </style>
    <h1>🔱 SYNTHETIC MIND V34.0</h1>
    <div class="grid">
        <div class="card">STATUS<br><span style="color:white">{{ '⚡ ACTIVE' if s.is_running else '💤 IDLE' }}</span></div>
        <div class="card">SUCCESS<br><span style="font-size: 25px">{{ s.success }}</span></div>
        <div class="card">BANNED<br><span style="font-size: 25px; color:red">{{ s.banned }}</span></div>
        <div class="card">LOGS<br><span style="font-size: 25px">{{ logs|length }}</span></div>
    </div>
    <div class="log">
        {% for l in logs %}<div class="{{l.type}}">>> [{{l.time}}] {{l.msg}}</div>{% endfor %}
    </div>
    """, s=state, logs=Logger.logs)

# ==========================================
# ⚔️ BATTLEGROUND: SPAM ENGINE
# ==========================================

class SpamEngine:
    @staticmethod
    async def execute(phone, target):
        client = TelegramClient(os.path.join(Config.SESSION_DIR, phone), Config.API_ID, Config.API_HASH)
        try:
            await client.connect()
            if not await client.is_user_authorized():
                db = Database.load(); db[phone]['status'] = 'dead'; Database.save(db)
                state['banned'] += 1
                Logger.add(f"Acc {phone} đã hi sinh!", "error")
                return False

            await client(ReadHistoryRequest(peer=target, max_id=0))
            await asyncio.sleep(random.randint(5, 10))

            async with client.action(target, 'typing'):
                await asyncio.sleep(random.randint(15, 25))
                
                content = "{🔥 CHÉO REF NHANH|🚀 KÈO THƠM CHÉO REF|💎 HỘI CHÉO LINK UY TÍN}\n{✅ Trả link 100%|✅ Không scam|✅ Trả link ngay}\n👉 [THAM GIA]({link})"
                msg = HumanBrain.get_spintax(content).format(link=Config.LINK_NHOM)
                msg = HumanBrain.apply_invisible_hash(msg)

                await client.send_message(target, msg, link_preview=False)
                state['success'] += 1
                Logger.add(f"Acc {phone[:6]} rải quân tại {target}", "info")
                return True
        except Exception as e:
            state['fail'] += 1
            Logger.add(f"Lỗi {phone[:6]}: {e}", "error")
            return False
        finally:
            await client.disconnect()

# ==========================================
# 📡 MASTER BOT HANDLER
# ==========================================

master = TelegramClient('master_bot', Config.API_ID, Config.API_HASH)

@master.on(events.NewMessage(pattern='/start'))
async def master_ui(event):
    if event.sender_id != Config.ADMIN_ID: return
    db = Database.load()
    alive = len([p for p in db if db.get(p, {}).get('status') == 'active'])
    btns = [[Button.inline("🚀 PHÁT LỆNH", b"run"), Button.inline("🛑 DỪNG QUÂN", b"stop")]]
    await event.reply(f"🔱 **SYNTHETIC MIND V34.0**\n💂 Quân số: `{alive}` acc sống\n📊 Trạng thái: **{'RUNNING' if state['is_running'] else 'IDLE'}**", buttons=btns)

@master.on(events.CallbackQuery())
async def cb(event):
    if event.data == b"run": await event.edit("🎯 **Nhập list nhóm mục tiêu (cách nhau bởi dấu phẩy):**")
    elif event.data == b"stop": state['is_running'] = False; await event.edit("🛑 Đã thu quân.")

@master.on(events.NewMessage(pattern='/add_acc'))
async def add_acc(event):
    if event.sender_id != Config.ADMIN_ID: return
    async with event.client.conversation(event.chat_id) as conv:
        await conv.send_message("📱 Số điện thoại:")
        phone = (await conv.get_response()).text.strip()
        client = TelegramClient(os.path.join(Config.SESSION_DIR, phone), Config.API_ID, Config.API_HASH)
        await client.connect()
        try:
            await client.send_code_request(phone)
            await conv.send_message("📩 OTP:")
            await client.sign_in(phone, (await conv.get_response()).text.strip())
        except Exception as e:
            await conv.send_message(f"Lỗi: {e}"); return
        
        db = Database.load(); db[phone] = {"status": "active"}; Database.save(db)
        await conv.send_message("✅ Đã kết nạp chiến binh mới!")

# ==========================================
# 🤖 AI AUTO-REPLY MODULE (NÂNG CẤP)
# ==========================================

async def ai_auto_reply(event):
    if event.is_private or not event.sender: return
    
    # Từ khóa để nhận diện tin nhắn chéo
    keywords = ["chéo", "ref", "check", "inbox", "link"]
    if any(key in event.raw_text.lower() for key in keywords):
        
        # Mẫu trả lời tự động bao gồm @ người dùng
        reply_templates = [
            f"✅ Trả link ngay bạn ơi! {Config.LINK_NHOM}",
            f"🚀 @{event.sender.username} Check link mình nhé {Config.LINK_NHOM}",
            f"💎 Uy tín trả nhanh nha {Config.LINK_NHOM}"
        ]
        
        await asyncio.sleep(random.randint(2, 5)) # Giả lập thời gian suy nghĩ
        await event.reply(random.choice(reply_templates))
        Logger.add(f"AI trả lời @{event.sender.username} trong nhóm {event.chat_id}", "warn")

# ==========================================
# 🚀 MISSION RUNNER
# ==========================================

@master.on(events.NewMessage())
async def run_mission(event):
    if event.sender_id != Config.ADMIN_ID or not event.text.startswith('@'): return
    targets = [t.strip() for t in event.text.split(',')]
    state['is_running'] = True
    Logger.add("KÍCH HOẠT CHIẾN DỊCH TỔNG LỰC", "warn")

    while state['is_running']:
        db = Database.load()
        active_accs = [p for p in db if db.get(p, {}).get('status') == 'active']
        if not active_accs: break

        for target in targets:
            if not state['is_running']: break
            phone = random.choice(active_accs)
            
            # 1. Spam theo lịch
            await SpamEngine.execute(phone, target)
            
            # 2. Nghỉ giữa các lệnh spam
            await asyncio.sleep(random.randint(Config.INTERVAL - 10, Config.INTERVAL + 10))

async def boot():
    if not os.path.exists(Config.SESSION_DIR): os.makedirs(Config.SESSION_DIR)
    await master.start(bot_token=Config.BOT_TOKEN)
    
    # Kích hoạt AI phản hồi cho tất cả acc
    db = Database.load()
    for phone in db:
        if db[phone]['status'] == 'active':
            c = TelegramClient(os.path.join(Config.SESSION_DIR, phone), Config.API_ID, Config.API_HASH)
            c.add_event_handler(ai_auto_reply, events.NewMessage(incoming=True))
            try: await c.start()
            except: pass
            
    Logger.add("Hệ thống Synthetic Mind V34.0 đã trực tuyến", "info")
    await master.run_until_disconnected()

if __name__ == "__main__":
    Thread(target=lambda: app.run(host='0.0.0.0', port=10000), daemon=True).start()
    asyncio.run(boot())
                                                              
