import os, re, requests, json, random, asyncio
from datetime import datetime, timedelta
from threading import Thread
from flask import Flask, request, jsonify
# Sửa import để tương thích bản 13.15
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, ParseMode
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, MessageHandler, Filters
import psycopg2
from psycopg2.extras import RealDictCursor

# ==========================================
# ⚙️ CẤU HÌNH HỆ THỐNG
# ==========================================
TOKEN = "8755060469:AAEfrc5Gj5Crr6RxP9gnxDrehbL_W7NsjIE"
ADMIN_ID = 7816353760
# LƯU Ý: Phải dùng cổng 6543 của Pooler để không bị lỗi mạng
DB_URL = "postgresql://postgres.naghdswctyyvzfdnforu:96886693002613@aws-1-ap-southeast-2.pooler.supabase.com:6543/postgres"
CHANNEL_ID = "@TRUMTXCL"
SUPPORT_LINK = "https://t.me/nth_dev"
MIN_DEPOSIT_RUT = 30000

BANK_NAME = "MSB (Maritime Bank)"
BANK_ACC = "96886693002613"
BANK_USER = "NGUYEN THANH HOP"

# ==========================================
# 🗄️ MODULE DATABASE
# ==========================================
class Database:
    def __init__(self):
        # Kết nối với SSL yêu cầu cho Supabase
        self.conn = psycopg2.connect(DB_URL, sslmode='require')
        self.setup()

    def setup(self):
        with self.conn.cursor() as cur:
            cur.execute('''CREATE TABLE IF NOT EXISTS users (
                uid BIGINT PRIMARY KEY, username TEXT, balance DOUBLE PRECISION DEFAULT 0,
                total_deposit DOUBLE PRECISION DEFAULT 0, total_bet DOUBLE PRECISION DEFAULT 0,
                ref_by BIGINT DEFAULT 0, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
            cur.execute('''CREATE TABLE IF NOT EXISTS giftcodes (
                code TEXT PRIMARY KEY, amount REAL, max_uses INTEGER, used_count INTEGER DEFAULT 0)''')
            cur.execute('''CREATE TABLE IF NOT EXISTS gift_history (uid BIGINT, code TEXT, PRIMARY KEY(uid, code))''')
            cur.execute('''CREATE TABLE IF NOT EXISTS trans_logs (id TEXT PRIMARY KEY, uid BIGINT, amount REAL)''')
            cur.execute("CREATE TABLE IF NOT EXISTS system_config (key TEXT PRIMARY KEY, value REAL)")
            cur.execute("INSERT INTO system_config VALUES ('win_rate', 50) ON CONFLICT DO NOTHING")
            cur.execute("INSERT INTO system_config VALUES ('force_result', -1) ON CONFLICT DO NOTHING")
            cur.execute('''CREATE TABLE IF NOT EXISTS checkins (uid BIGINT, date DATE, PRIMARY KEY(uid, date))''')
            self.conn.commit()

    def get_user(self, uid):
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM users WHERE uid = %s", (uid,))
            return cur.fetchone()

db = Database()

# ==========================================
# 💰 MODULE AUTO BANK SEPAY (MSB)
# ==========================================
app_flask = Flask(__name__)

def send_tele_msg(chat_id, text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"})

@app_flask.route('/webhook/sepay', methods=['POST'])
def sepay_webhook():
    data = request.json
    content = data.get('transactionContent', '').upper()
    amount = float(data.get('transferAmount', 0))
    trans_id = str(data.get('id'))
    match = re.search(r'\d{6,15}', content)
    if match:
        uid = int(match.group())
        with db.conn.cursor() as cur:
            cur.execute("SELECT 1 FROM trans_logs WHERE id = %s", (trans_id,))
            if not cur.fetchone():
                cur.execute("UPDATE users SET balance = balance + %s, total_deposit = total_deposit + %s WHERE uid = %s", (amount, amount, uid))
                cur.execute("INSERT INTO trans_logs (id, uid, amount) VALUES (%s, %s, %s)", (trans_id, uid, amount))
                db.conn.commit()
                send_tele_msg(uid, f"✅ **AUTO NẠP THÀNH CÔNG**\n💰 Số dư: `+{amount:,.0f}đ`\n🔥 Chúc bạn chơi game vui vẻ!")
                send_tele_msg(ADMIN_ID, f"💰 **THÔNG BÁO:** ID `{uid}` vừa nạp `{amount:,.0f}đ` tự động qua MSB.")
    return jsonify({"status": "ok"}), 200

# ==========================================
# 🎮 HANDLERS (BẢN 13.15)
# ==========================================
def start(update, context):
    uid = update.effective_user.id
    user = db.get_user(uid)
    if not user:
        ref = int(context.args[0]) if context.args and context.args[0].isdigit() else 0
        with db.conn.cursor() as cur:
            cur.execute("INSERT INTO users (uid, username, ref_by) VALUES (%s, %s, %s) ON CONFLICT DO NOTHING", 
                        (uid, update.effective_user.username, ref))
            db.conn.commit()
        user = db.get_user(uid)

    txt = (f"🚀 **TRUMTX - CASINO ĐẲNG CẤP 2026**\n"
           f"────────────────────\n"
           f"🆔 ID: `{uid}`\n"
           f"💰 Số dư: `{user['balance']:,.0f}đ`\n"
           f"📥 Tổng nạp: `{user['total_deposit']:,.0f}đ`\n"
           f"🤝 Hoa hồng: `{(user['total_bet']*0.005):,.0f}đ`\n"
           f"────────────────────\n"
           f"⚠️ *Điều kiện rút:* Nạp tích lũy đủ **30,000đ**")
    
    kb = [
        [InlineKeyboardButton("🎲 TÀI XỈU", callback_data='game_tx'), InlineKeyboardButton("🎡 VÒNG QUAY", callback_data='wheel')],
        [InlineKeyboardButton("💵 NẠP TIỀN", callback_data='nap'), InlineKeyboardButton("💸 RÚT TIỀN", callback_data='rut')],
        [InlineKeyboardButton("🎁 GIFTCODE", callback_data='gift'), InlineKeyboardButton("🎯 NHIỆM VỤ", callback_data='mission')],
        [InlineKeyboardButton("🤝 ĐẠI LÝ", callback_data='affiliate'), InlineKeyboardButton("📞 HỖ TRỢ", url=SUPPORT_LINK)]
    ]
    update.message.reply_text(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.MARKDOWN)

def handle_callback(update, context):
    query = update.callback_query
    uid = query.from_user.id
    user = db.get_user(uid)
    data = query.data

    if data == 'nap':
        txt = (f"🏦 **NẠP TIỀN TỰ ĐỘNG (MSB)**\n"
               f"────────────────────\n"
               f"🏧 Ngân hàng: `{BANK_NAME}`\n"
               f"🔢 STK: `{BANK_ACC}`\n"
               f"👤 Chủ TK: `{BANK_USER}`\n"
               f"📝 Nội dung: `{uid}`\n"
               f"────────────────────\n"
               f"⚠️ **Lưu ý:** Chuyển đúng nội dung là ID của bạn!")
        query.message.reply_text(txt, parse_mode=ParseMode.MARKDOWN)

    elif data == 'rut':
        if user['total_deposit'] < MIN_DEPOSIT_RUT:
            query.answer(f"❌ Cần nạp đủ {MIN_DEPOSIT_RUT:,.0f}đ!", show_alert=True)
        else:
            query.message.reply_text("Gõ: `/rut [Số_tiền] [STK] [Ngân_hàng]`")

    elif data == 'mission':
        today = datetime.now().date()
        with db.conn.cursor() as cur:
            cur.execute("SELECT 1 FROM checkins WHERE uid = %s AND date = %s", (uid, today))
            if cur.fetchone():
                query.answer("❌ Đã điểm danh rồi!", show_alert=True)
            else:
                bonus = random.randint(1000, 3000)
                cur.execute("INSERT INTO checkins VALUES (%s, %s)", (uid, today))
                cur.execute("UPDATE users SET balance = balance + %s WHERE uid = %s", (bonus, uid))
                db.conn.commit()
                query.answer(f"✅ +{bonus:,.0f}đ", show_alert=True)

# ==========================================
# 👑 ADMIN PANEL (BẢN 13.15)
# ==========================================
def admin_panel(update, context):
    if update.effective_user.id != ADMIN_ID: return
    with db.conn.cursor() as cur:
        cur.execute("SELECT COUNT(*), SUM(balance), SUM(total_deposit) FROM users")
        s = cur.fetchone()
        cur.execute("SELECT value FROM system_config WHERE key = 'win_rate'")
        rate = cur.fetchone()[0]
    
    txt = (f"👑 **ADMIN PANEL**\n"
           f"👥 Khách: `{s[0]}`\n"
           f"💰 Ví khách: `{s[1] or 0:,.0f}đ`\n"
           f"📈 Thắng: `{rate}%`\n"
           f"🛠 Lệnh: /rate, /force, /duyet")
    update.message.reply_text(txt, parse_mode=ParseMode.MARKDOWN)

def admin_duyet_rut(update, context):
    if update.effective_user.id != ADMIN_ID: return
    try:
        target_uid = int(context.args[0])
        amt = float(context.args[1])
        with db.conn.cursor() as cur:
            cur.execute("UPDATE users SET balance = balance - %s WHERE uid = %s", (amt, target_uid))
            db.conn.commit()
        send_tele_msg(target_uid, f"✅ Admin đã chuyển `{amt:,.0f}đ`!")
        update.message.reply_text("✅ Đã duyệt!")
    except: update.message.reply_text("Lỗi cú pháp!")

# ==========================================
# 🚀 RUNNING
# ==========================================
def run_flask():
    app_flask.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))

if __name__ == '__main__':
    Thread(target=run_flask).start()
    # Dùng Updater thay cho Application (v13.15)
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher
    
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("admin", admin_panel))
    dp.add_handler(CommandHandler("duyet", admin_duyet_rut))
    dp.add_handler(CallbackQueryHandler(handle_callback))
    
    print("🚀 TRUMTX SUPREME IS ONLINE!")
    updater.start_polling()
    updater.idle()
    
