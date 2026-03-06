import os, re, requests, json, random, asyncio
from datetime import datetime, timedelta
from threading import Thread
from flask import Flask, request, jsonify
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
import psycopg2
from psycopg2.extras import RealDictCursor

# ==========================================
# ⚙️ CẤU HÌNH HỆ THỐNG (THAY Ở ĐÂY)
# ==========================================
TOKEN = "8755060469:AAEfrc5Gj5Crr6RxP9gnxDrehbL_W7NsjIE"
ADMIN_ID = 7816353760  # ID Telegram của bạn
DB_URL = "postgresql://postgres.naghdswctyyvzfdnforu:[96886693002613]@aws-1-ap-southeast-2.pooler.supabase.com:5432/postgres" # Link Database Supabase
CHANNEL_ID = "@TRUMTXCL" # Kênh nổ hũ/rút tiền
SUPPORT_LINK = "https://t.me/nth_dev"
MIN_DEPOSIT_RUT = 30000 # Nạp đủ 30k mới mở khóa rút

# Thông tin hiển thị nạp
BANK_NAME = "MSB (Maritime Bank)"
BANK_ACC = "96886693002613"
BANK_USER = "NGUYEN THANH HOP"

# ==========================================
# 🗄️ MODULE DATABASE (ANTI-CLONE & LOGS)
# ==========================================
class Database:
    def __init__(self):
        self.conn = psycopg2.connect(DB_URL, sslmode='require')
        self.setup()

    def setup(self):
        with self.conn.cursor() as cur:
            # Bảng Người dùng
            cur.execute('''CREATE TABLE IF NOT EXISTS users (
                uid BIGINT PRIMARY KEY, username TEXT, balance DOUBLE PRECISION DEFAULT 0,
                total_deposit DOUBLE PRECISION DEFAULT 0, total_bet DOUBLE PRECISION DEFAULT 0,
                ref_by BIGINT DEFAULT 0, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
            # Bảng Giftcode
            cur.execute('''CREATE TABLE IF NOT EXISTS giftcodes (
                code TEXT PRIMARY KEY, amount REAL, max_uses INTEGER, used_count INTEGER DEFAULT 0)''')
            cur.execute('''CREATE TABLE IF NOT EXISTS gift_history (uid BIGINT, code TEXT, PRIMARY KEY(uid, code))''')
            # Bảng Giao dịch SePay (Chống cộng đúp)
            cur.execute('''CREATE TABLE IF NOT EXISTS trans_logs (id TEXT PRIMARY KEY, uid BIGINT, amount REAL)''')
            # Bảng Cấu hình Bẻ Cầu
            cur.execute("CREATE TABLE IF NOT EXISTS system_config (key TEXT PRIMARY KEY, value REAL)")
            cur.execute("INSERT INTO system_config VALUES ('win_rate', 50) ON CONFLICT DO NOTHING")
            cur.execute("INSERT INTO system_config VALUES ('force_result', -1) ON CONFLICT DO NOTHING")
            # Bảng Điểm danh hằng ngày
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

    # Regex tìm ID khách trong nội dung nạp (Ví dụ: "NAP 123456")
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
# 🎲 MODULE GAME LOGIC (TÀI XỈU - BẺ CẦU)
# ==========================================
def get_game_result():
    with db.conn.cursor() as cur:
        # Check ép kết quả
        cur.execute("SELECT value FROM system_config WHERE key = 'force_result'")
        force = int(cur.fetchone()[0])
        if force != -1: return force # 1: Tài, 0: Xỉu
        
        # Check tỉ lệ thắng %
        cur.execute("SELECT value FROM system_config WHERE key = 'win_rate'")
        rate = cur.fetchone()[0]
        return 1 if random.randint(1, 100) <= rate else 0

# ==========================================
# 🎮 HANDLERS: MENU & CHỨC NĂNG
# ==========================================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
    await update.message.reply_text(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.MARKDOWN)

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
               f"⚠️ **Lưu ý:** Chuyển đúng nội dung là ID của bạn để được cộng tiền tự động sau 30 giây!")
        await query.message.reply_text(txt, parse_mode=ParseMode.MARKDOWN)

    elif data == 'rut':
        if user['total_deposit'] < MIN_DEPOSIT_RUT:
            await query.answer(f"❌ Bạn cần nạp đủ {MIN_DEPOSIT_RUT:,.0f}đ để mở khóa rút!", show_alert=True)
        else:
            await query.message.reply_text("Để rút tiền, vui lòng gõ: `/rut [Số_tiền] [STK] [Ngân_hàng]`")

    elif data == 'gift':
        await query.message.reply_text("🎁 Nhập Giftcode bằng cách gõ: `/code [Mã_của_bạn]`")

    elif data == 'mission':
        # Logic điểm danh đơn giản
        today = datetime.now().date()
        with db.conn.cursor() as cur:
            cur.execute("SELECT 1 FROM checkins WHERE uid = %s AND date = %s", (uid, today))
            if cur.fetchone():
                await query.answer("❌ Hôm nay bạn đã điểm danh rồi!", show_alert=True)
            else:
                bonus = random.randint(1000, 3000)
                cur.execute("INSERT INTO checkins VALUES (%s, %s)", (uid, today))
                cur.execute("UPDATE users SET balance = balance + %s WHERE uid = %s", (bonus, uid))
                db.conn.commit()
                await query.answer(f"✅ Điểm danh thành công! +{bonus:,.0f}đ", show_alert=True)

    elif data == 'affiliate':
        link = f"https://t.me/{context.bot.username}?start={uid}"
        await query.message.reply_text(f"🤝 **CHƯƠNG TRÌNH ĐẠI LÝ**\nLink của bạn: `{link}`\nNhận 0.5% mỗi khi bạn bè đặt cược!")

# ==========================================
# 👑 MODULE ADMIN SUPREME PANEL
# ==========================================
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    with db.conn.cursor() as cur:
        cur.execute("SELECT COUNT(*), SUM(balance), SUM(total_deposit) FROM users")
        s = cur.fetchone()
        cur.execute("SELECT value FROM system_config WHERE key = 'win_rate'")
        rate = cur.fetchone()[0]
    
    txt = (f"👑 **QUẢN TRỊ VIÊN SUPREME**\n"
           f"────────────────────\n"
           f"👥 Tổng khách: `{s[0]}`\n"
           f"💰 Tiền trong ví khách: `{s[1] or 0:,.0f}đ`\n"
           f"📥 Doanh thu nạp: `{s[2] or 0:,.0f}đ`\n"
           f"📈 Tỉ lệ thắng hiện tại: `{rate}%`\n"
           f"────────────────────\n"
           f"🛠 **Lệnh điều khiển:**\n"
           f"1️⃣ Chỉnh % thắng: `/rate [0-100]`\n"
           f"2️⃣ Ép kết quả: `/force [1 hoặc 0]` (-1 để hủy)\n"
           f"3️⃣ Set tiền: `/set [ID] [Tiền]`\n"
           f"4️⃣ Tạo code: `/makecode [Mã] [Tiền] [Lượt]`\n"
           f"5️⃣ Duyệt rút: `/duyet [ID] [Tiền]`")
    await update.message.reply_text(txt, parse_mode=ParseMode.MARKDOWN)

async def admin_duyet_rut(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    try:
        target_uid = int(context.args[0])
        amt = float(context.args[1])
        # Trừ tiền khách
        with db.conn.cursor() as cur:
            cur.execute("UPDATE users SET balance = balance - %s WHERE uid = %s", (amt, target_uid))
            db.conn.commit()
        
        # Báo khách
        send_tele_msg(target_uid, f"✅ **RÚT TIỀN THÀNH CÔNG**\nSố tiền `{amt:,.0f}đ` đã được Admin chuyển khoản!")
        
        # Nổ kênh thông báo
        masked = str(target_uid)[:4] + "xxxx"
        msg_channel = (f"🔔 **THÔNG BÁO RÚT TIỀN**\n"
                       f"👤 Khách hàng: `Người chơi {masked}`\n"
                       f"💰 Số tiền: `{amt:,.0f} VNĐ`\n"
                       f"✅ Trạng thái: **Đã thanh toán**\n"
                       f"🎮 Bot: @{context.bot.username}")
        await context.bot.send_message(CHANNEL_ID, msg_channel)
        await update.message.reply_text(f"✅ Đã duyệt rút và nổ kênh cho ID {target_uid}")
    except: await update.message.reply_text("Cú pháp: `/duyet [ID] [Số_tiền]`")

async def admin_set_rate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    rate = float(context.args[0])
    with db.conn.cursor() as cur:
        cur.execute("UPDATE system_config SET value = %s WHERE key = 'win_rate'", (rate,))
        db.conn.commit()
    await update.message.reply_text(f"✅ Đã chỉnh tỉ lệ thắng về `{rate}%`")

async def admin_force(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    val = int(context.args[0])
    with db.conn.cursor() as cur:
        cur.execute("UPDATE system_config SET value = %s WHERE key = 'force_result'", (val,))
        db.conn.commit()
    status = "TÀI/CHẴN" if val == 1 else "XỈU/LẺ"
    if val == -1: status = "NGẪU NHIÊN"
    await update.message.reply_text(f"✅ Đã ép kết quả ván tiếp theo: `{status}`")

# ==========================================
# 🚀 KHỞI CHẠY (BOT + FLASK)
# ==========================================
def run_flask():
    app_flask.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))

if __name__ == '__main__':
    Thread(target=run_flask).start()
    app = Application.builder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin_panel))
    app.add_handler(CommandHandler("rate", admin_set_rate))
    app.add_handler(CommandHandler("force", admin_force))
    app.add_handler(CommandHandler("duyet", admin_duyet_rut))
    app.add_handler(CallbackQueryHandler(handle_callback))
    
    print("🚀 TRUMTX SUPREME IS ONLINE!")
    app.run_polling()
    
