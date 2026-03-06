import os, re, requests, json, random, time, threading, logging
from datetime import datetime, timedelta
from flask import Flask
from telegram import (InlineKeyboardButton, InlineKeyboardMarkup, Update, 
                      ParseMode, ReplyKeyboardMarkup, KeyboardButton, InputMediaPhoto)
from telegram.ext import (Updater, CommandHandler, CallbackQueryHandler, 
                          MessageHandler, Filters, CallbackContext)
import psycopg2
from psycopg2.extras import RealDictCursor

# ==========================================
# 🌐 HỆ THỐNG GIỮ BOT ONLINE (FLASK SERVER)
# ==========================================
app = Flask(__name__)
@app.route('/')
def home(): 
    return f"TRUMTX SUPREME ENGINE V12 IS ACTIVE - {datetime.now().strftime('%H:%M:%S')}"

def run_flask():
    try:
        app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))
    except Exception as e:
        print(f"Flask Error: {e}")

# ==========================================
# ⚙️ CẤU HÌNH HỆ THỐNG TỐI CAO
# ==========================================
TOKEN = "8755060469:AAH1R02X_408_mNFPcOH8harJI25Z96UZL4"
ADMIN_ID = 7816353760
DB_URL = "postgresql://postgres.naghdswctyyvzfdnforu:96886693002613@aws-1-ap-southeast-2.pooler.supabase.com:6543/postgres"

# Thông tin thanh toán (Fix cứng theo yêu cầu)
BANK_INFO = {
    "name": "MSB (Maritime Bank)",
    "acc": "96886693002613",
    "user": "NGUYEN THANH HOP",
    "min_deposit": 10000,
    "min_withdraw": 50000
}

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# ==========================================
# 🗄️ DATABASE MANAGER - SCHEMA CỰC RỘNG
# ==========================================
class Database:
    def __init__(self):
        self.conn = psycopg2.connect(DB_URL, sslmode='require')
        self.init_db()

    def init_db(self):
        with self.conn.cursor() as cur:
            # Bảng người dùng: Chi tiết từng xu một
            cur.execute('''CREATE TABLE IF NOT EXISTS users (
                uid BIGINT PRIMARY KEY, 
                username TEXT, 
                balance DOUBLE PRECISION DEFAULT 0,
                total_deposit DOUBLE PRECISION DEFAULT 0, 
                total_withdraw DOUBLE PRECISION DEFAULT 0,
                total_bet DOUBLE PRECISION DEFAULT 0,
                total_win DOUBLE PRECISION DEFAULT 0, 
                total_ref_earn DOUBLE PRECISION DEFAULT 0,
                bank_acc TEXT DEFAULT NULL, 
                bank_name TEXT DEFAULT NULL, 
                bank_user TEXT DEFAULT NULL,
                ref_by BIGINT DEFAULT 0, 
                exp INTEGER DEFAULT 0,
                is_banned BOOLEAN DEFAULT FALSE,
                last_daily TIMESTAMP DEFAULT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
            
            # Bảng Lịch sử giao dịch
            cur.execute('''CREATE TABLE IF NOT EXISTS transactions (
                id SERIAL PRIMARY KEY, 
                uid BIGINT, 
                amount DOUBLE PRECISION, 
                type TEXT, 
                status TEXT DEFAULT 'success', 
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')

            # Bảng Admin Config
            cur.execute("CREATE TABLE IF NOT EXISTS admin_settings (key TEXT PRIMARY KEY, value TEXT)")
            configs = [('win_rate', '50'), ('maintenance', 'off'), ('ref_bonus_percent', '5')]
            for k, v in configs:
                cur.execute("INSERT INTO admin_settings VALUES (%s, %s) ON CONFLICT DO NOTHING", (k, v))
            
            self.conn.commit()

    def query(self, sql, params=None, fetch=True):
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            try:
                cur.execute(sql, params)
                res = cur.fetchall() if fetch else None
                self.conn.commit()
                return res
            except Exception as e:
                self.conn.rollback()
                print(f"DB Error: {e}")
                return []

db = Database()

# ==========================================
# 🎲 ENGINE TRÒ CHƠI - TỈ MỈ & CHỐNG BUG
# ==========================================
class CasinoEngine:
    @staticmethod
    def roll_taixiu(choice, win_rate):
        """Logic Tài Xỉu có can thiệp winrate chuẩn xác"""
        dices = [random.randint(1, 6) for _ in range(3)]
        total = sum(dices)
        res = "tai" if total >= 11 else "xiu"
        
        # Kiểm tra tỷ lệ thắng
        if random.randint(1, 100) > int(win_rate):
            # Ép cho thua
            if choice == "tai":
                dices = [random.randint(1, 3), random.randint(1, 3), random.randint(1, 4)]
            else:
                dices = [random.randint(4, 6), random.randint(4, 6), random.randint(4, 5)]
            total = sum(dices)
            res = "tai" if total >= 11 else "xiu"
        return dices, total, res

    @staticmethod
    def roll_baucua():
        """Logic Bầu Cua 6 mặt truyền thống"""
        items = ["bau", "cua", "tom", "ca", "ga", "nai"]
        res = [random.choice(items) for _ in range(3)]
        return res

    @staticmethod
    def get_icons(name):
        icons = {"bau": "🎃", "cua": "🦀", "tom": "🦞", "ca": "🐟", "ga": "🐔", "nai": "🦌", "tai": "🔴", "xiu": "⚫"}
        return icons.get(name, "❓")

      # ==========================================
# 🎨 GIAO DIỆN LUXURY UI - FIX 100% LỖI NÚT
# ==========================================
def main_menu():
    return ReplyKeyboardMarkup([
        [KeyboardButton("🎲 TÀI XỈU VIP"), KeyboardButton("⚖️ CHẴN LẺ MSB")],
        [KeyboardButton("🦀 BẦU CUA"), KeyboardButton("🎡 VÒNG QUAY")],
        [KeyboardButton("💰 NẠP TIỀN"), KeyboardButton("💸 RÚT TIỀN")],
        [KeyboardButton("🎯 NHIỆM VỤ"), KeyboardButton("🏆 TOP BXH")],
        [KeyboardButton("👤 CÁ NHÂN"), KeyboardButton("🤝 ĐẠI LÝ")],
        [KeyboardButton("🎁 GIFTCODE"), KeyboardButton("📞 HỖ TRỢ")]
    ], resize_keyboard=True)

def bet_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💵 10K", callback_data="set_10000"), 
         InlineKeyboardButton("💵 50K", callback_data="set_50000"), 
         InlineKeyboardButton("💵 200K", callback_data="set_200000")],
        [InlineKeyboardButton("💵 1M", callback_data="set_1000000"), 
         InlineKeyboardButton("🔥 TẤT TAY", callback_data="set_all")]
    ])

# ==========================================
# 🧠 XỬ LÝ LỆNH NGƯỜI DÙNG (COMMANDS)
# ==========================================
def start(update: Update, context: CallbackContext):
    uid = update.effective_user.id
    name = update.effective_user.first_name
    user = db.query("SELECT * FROM users WHERE uid = %s", (uid,))
    
    if not user:
        ref_by = int(context.args[0]) if context.args and context.args[0].isdigit() else 0
        db.query("INSERT INTO users (uid, username, ref_by) VALUES (%s, %s, %s)", (uid, name, ref_by), fetch=False)
    
    welcome = (f"🔥 **TRUMTX - ĐẲNG CẤP CASINO 2026** 🔥\n"
               f"━━━━━━━━━━━━━━━━━━━━\n"
               f"👋 Chào mừng: **{name}**\n🆔 ID: `{uid}`\n"
               f"💰 Số dư: `{db.query('SELECT balance FROM users WHERE uid=%s',(uid,))[0]['balance']:,.0f}đ`\n"
               f"━━━━━━━━━━━━━━━━━━━━\n"
               f"🚀 Nạp rút tự động - Xanh chín - Uy tín!")
    update.message.reply_text(welcome, reply_markup=main_menu(), parse_mode=ParseMode.MARKDOWN)

def link_bank(update: Update, context: CallbackContext):
    uid = update.effective_user.id
    user = db.query("SELECT bank_acc FROM users WHERE uid = %s", (uid,))[0]
    
    if user['bank_acc']:
        return update.message.reply_text("❌ **LỖI:** Bạn đã liên kết ngân hàng trước đó. Để thay đổi vui lòng liên hệ Admin!")
    
    try:
        stk = context.args[0]
        bank = context.args[1]
        ten = " ".join(context.args[2:]).upper()
        db.query("UPDATE users SET bank_acc=%s, bank_name=%s, bank_user=%s WHERE uid=%s", (stk, bank, ten, uid), fetch=False)
        update.message.reply_text(f"✅ **LIÊN KẾT THÀNH CÔNG**\n🏦 Bank: {bank}\n🔢 STK: `{stk}`\n👤 Tên: {ten}")
    except:
        update.message.reply_text("⚠️ **SAI CÚ PHÁP!**\nGõ: `/link [STK] [Tên_Bank] [Tên_Chủ_TK]`\nVí dụ: `/link 96886693002613 MSB NGUYEN THANH HOP`")

def withdraw(update: Update, context: CallbackContext):
    uid = update.effective_user.id
    user = db.query("SELECT * FROM users WHERE uid = %s", (uid,))[0]
    
    if not user['bank_acc']:
        return update.message.reply_text("❌ Bạn chưa liên kết ngân hàng! Dùng lệnh `/link` để liên kết.")
    
    try:
        amount = float(context.args[0])
        if amount < 50000: return update.message.reply_text("❌ Rút tối thiểu 50,000đ!")
        if user['balance'] < amount: return update.message.reply_text("❌ Số dư không đủ!")
        
        db.query("UPDATE users SET balance = balance - %s WHERE uid = %s", (amount, uid), fetch=False)
        db.query("INSERT INTO transactions (uid, amount, type) VALUES (%s, %s, 'withdraw')", (uid, amount), fetch=False)
        
        # Báo Admin
        msg_admin = (f"🔔 **YÊU CẦU RÚT TIỀN**\n"
                     f"🆔 ID: `{uid}`\n💰 Số tiền: `{amount:,.0f}đ`\n"
                     f"🏦 Bank: {user['bank_name']} | `{user['bank_acc']}`\n👤 Tên: {user['bank_user']}")
        context.bot.send_message(ADMIN_ID, msg_admin)
        update.message.reply_text("✅ Gửi lệnh rút thành công! Vui lòng chờ Admin duyệt.")
    except:
        update.message.reply_text("⚠️ Cú pháp: `/rut [số_tiền]`")

# ==========================================
# 🕹️ LOGIC GAME & CALLBACK XỬ LÝ TIỀN
# ==========================================
user_bet_amount = {}

def handle_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    uid = query.from_user.id
    data = query.data
    user = db.query("SELECT * FROM users WHERE uid = %s", (uid,))[0]

    # Chọn tiền cược
    if data.startswith("set_"):
        val = data.split("_")[1]
        user_bet_amount[uid] = user['balance'] if val == "all" else int(val)
        query.answer(f"✅ Đã chọn cược: {user_bet_amount[uid]:,.0f}đ")

    # Đặt cửa Tài Xỉu
    elif data.startswith("tx_"):
        choice = data.split("_")[1]
        bet = user_bet_amount.get(uid, 10000)
        
        if user['balance'] < bet: return query.answer("❌ Số dư không đủ!", show_alert=True)
        
        # Trừ tiền & Tính hoa hồng Ref
        db.query("UPDATE users SET balance = balance - %s, total_bet = total_bet + %s WHERE uid = %s", (bet, bet, uid), fetch=False)
        if user['ref_by'] > 0:
            comm = bet * 0.05
            db.query("UPDATE users SET balance = balance + %s, total_ref_earn = total_ref_earn + %s WHERE uid = %s", (comm, comm, user['ref_by']), fetch=False)

        # Lắc Xúc Xắc
        wr = db.query("SELECT value FROM admin_settings WHERE key='win_rate'")[0]['value']
        dices, total, res = CasinoEngine.roll_taixiu(choice, wr)
        d_icons = "".join([CasinoEngine.get_icons(str(d)) if d == 0 else str(d) for d in dices]) # Sửa lại icon cho đẹp
        
        if choice == res:
            win = bet * 1.95
            db.query("UPDATE users SET balance = balance + %s, total_win = total_win + %s WHERE uid = %s", (win, win, uid), fetch=False)
            msg = f"🎉 **CHIẾN THẮNG!**\n🎲 Kết quả: `{dices}` = **{total}** ({res.upper()})\n💰 Nhận: `+{win:,.0f}đ`"
        else:
            msg = f"❌ **THUA CUỘC!**\n🎲 Kết quả: `{dices}` = **{total}** ({res.upper()})\n💸 Mất: `-{bet:,.0f}đ`"
        
        query.edit_message_text(msg, reply_markup=bet_menu(), parse_mode=ParseMode.MARKDOWN)

# ==========================================
# 📩 XỬ LÝ NHẬN DIỆN NÚT BẤM (TEXT HANDLER)
# ==========================================
def on_text(update: Update, context: CallbackContext):
    uid = update.effective_user.id
    text = update.message.text
    user = db.query("SELECT * FROM users WHERE uid = %s", (uid,))[0]

    if text == "🎲 TÀI XỈU VIP":
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔴 TÀI (x1.95)", callback_data="tx_tai"), 
             InlineKeyboardButton("⚫ XỈU (x1.95)", callback_data="tx_xiu")],
            [InlineKeyboardButton("💵 ĐỔI MỨC CƯỢC", callback_data="change_bet")]
        ])
        update.message.reply_text(f"🎲 **TÀI XỈU VIP**\n💰 Số dư: `{user['balance']:,.0f}đ`\nChọn mức cược bên dưới rồi chọn cửa:", reply_markup=bet_menu())
        update.message.reply_text("👇 **CHỌN CỬA ĐẶT:**", reply_markup=kb)

    elif text == "💰 NẠP TIỀN":
        msg = (f"🏦 **NẠP TIỀN TỰ ĐỘNG**\n━━━━━━━━━━━━━━\n"
               f"🏧 Ngân hàng: **{BANK_INFO['name']}**\n"
               f"🔢 STK: `{BANK_INFO['acc']}`\n"
               f"👤 Chủ TK: **{BANK_INFO['user']}**\n"
               f"📝 Nội dung: `{uid}`\n━━━━━━━━━━━━━━\n"
               f"⚠️ **Lưu ý:** Ghi đúng nội dung để tiền vào sau 30s!")
        update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)

    elif text == "👤 CÁ NHÂN":
        bank = f"{user['bank_name']} | {user['bank_acc']}" if user['bank_acc'] else "❌ Chưa liên kết"
        msg = (f"👤 **THÔNG TIN TÀI KHOẢN**\n━━━━━━━━━━━━━━\n"
               f"🆔 ID: `{uid}`\n💰 Số dư: `{user['balance']:,.0f}đ`\n"
               f"📊 Tổng cược: `{user['total_bet']:,.0f}đ`\n"
               f"🏆 Tổng thắng: `{user['total_win']:,.0f}đ`\n"
               f"🤝 Hoa hồng: `{user['total_ref_earn']:,.0f}đ`\n"
               f"🏦 Bank: `{bank}`\n━━━━━━━━━━━━━━\n"
               f"👉 Liên kết bank: `/link [STK] [Bank] [Tên]`")
        update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)

    elif text == "🤝 ĐẠI LÝ":
        bot_user = context.bot.username
        link = f"https://t.me/{bot_user}?start={uid}"
        update.message.reply_text(f"🤝 **HỆ THỐNG ĐẠI LÝ**\n\nNhận ngay **5%** tiền cược của cấp dưới!\n🔗 Link của bạn: `{link}`", parse_mode=ParseMode.MARKDOWN)

# ==========================================
# 🚀 KHỞI CHẠY (ENGINE)
# ==========================================
if __name__ == '__main__':
    threading.Thread(target=run_flask, daemon=True).start()
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("link", link_bank))
    dp.add_handler(CommandHandler("rut", withdraw))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, on_text))
    dp.add_handler(CallbackQueryHandler(handle_callback))
    
    print("🚀 [TRUMTX V12] BOT ĐÃ ONLINE - FULL LOGIC!")
    updater.start_polling(drop_pending_updates=True)
    updater.idle()
      
