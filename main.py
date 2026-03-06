import os, re, requests, json, random, time, threading, logging
from flask import Flask
from datetime import datetime, timedelta
from telegram import (InlineKeyboardButton, InlineKeyboardMarkup, Update, 
                      ParseMode, ReplyKeyboardMarkup, KeyboardButton, InputMediaPhoto)
from telegram.ext import (Updater, CommandHandler, CallbackQueryHandler, 
                          MessageHandler, Filters, CallbackContext)
import psycopg2
from psycopg2.extras import RealDictCursor

# ==========================================
# 🌐 WEB SERVER (GIỮ BOT LUÔN ONLINE TRÊN RENDER)
# ==========================================
app = Flask(__name__)
@app.route('/')
def home(): return "Bot TRUMTX SUPREME is Running!"

def run_flask():
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))

# ==========================================
# ⚙️ CẤU HÌNH HỆ THỐNG TỐI CAO
# ==========================================
TOKEN = "8755060469:AAH1R02X_408_mNFPcOH8harJI25Z96UZL4"
ADMIN_ID = 7816353760
DB_URL = "postgresql://postgres.naghdswctyyvzfdnforu:96886693002613@aws-1-ap-southeast-2.pooler.supabase.com:6543/postgres"

# Thông tin bank mặc định
BANK_NAME = "MSB (Maritime Bank)"
BANK_ACC = "96886693002613"
BANK_USER = "NGUYEN THANH HOP"
GROUP_LINK = "https://t.me/TRUMTXCL" 
LOG_GROUP_ID = -1003778771904 

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# ==========================================
# 🗄️ DATABASE ENGINE - FULL SYSTEM
# ==========================================
class Database:
    def __init__(self):
        try:
            self.conn = psycopg2.connect(DB_URL, sslmode='require')
            self.setup()
        except Exception as e:
            print(f"Database Connect Error: {e}")

    def setup(self):
        with self.conn.cursor() as cur:
            # Bảng người dùng full field
            cur.execute('''CREATE TABLE IF NOT EXISTS users (
                uid BIGINT PRIMARY KEY, 
                username TEXT, 
                balance DOUBLE PRECISION DEFAULT 0,
                total_deposit DOUBLE PRECISION DEFAULT 0, 
                total_bet DOUBLE PRECISION DEFAULT 0,
                total_win DOUBLE PRECISION DEFAULT 0, 
                total_ref_earn DOUBLE PRECISION DEFAULT 0,
                bank_acc TEXT, bank_name TEXT, bank_user TEXT,
                ref_by BIGINT DEFAULT 0, 
                mission_count INTEGER DEFAULT 0,
                exp INTEGER DEFAULT 0,
                is_banned BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
            
            # Bảng rút tiền
            cur.execute('''CREATE TABLE IF NOT EXISTS withdraw_requests (
                id SERIAL PRIMARY KEY, 
                uid BIGINT, 
                amount DOUBLE PRECISION, 
                status TEXT DEFAULT 'pending', 
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
            
            # Bảng Giftcode
            cur.execute('''CREATE TABLE IF NOT EXISTS giftcodes (
                code TEXT PRIMARY KEY, 
                amount REAL, 
                limit_use INTEGER, 
                used INTEGER DEFAULT 0)''')

            # Bảng Config
            cur.execute("CREATE TABLE IF NOT EXISTS admin_config (key TEXT PRIMARY KEY, value TEXT)")
            configs = [
                ('win_rate', '50'), 
                ('min_withdraw', '50000'), 
                ('ref_percent', '5'),
                ('maintenance', 'false')
            ]
            for k, v in configs:
                cur.execute("INSERT INTO admin_config VALUES (%s, %s) ON CONFLICT DO NOTHING", (k, v))
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
                print(f"Query Error: {e}")
                return []

db = Database()

# ==========================================
# 🕹️ GAME ENGINES - LOGIC KHÔNG RÚT GỌN
# ==========================================
class GameEngine:
    @staticmethod
    def play_taixiu(choice, wr):
        dices = [random.randint(1, 6) for _ in range(3)]
        total = sum(dices)
        res = "tai" if total >= 11 else "xiu"
        # Can thiệp winrate
        if random.randint(1, 100) > int(wr):
            if choice == "tai":
                dices = [random.randint(1, 3), random.randint(1, 3), random.randint(1, 4)]
                total = sum(dices); res = "xiu"
            else:
                dices = [random.randint(4, 6), random.randint(4, 6), random.randint(4, 5)]
                total = sum(dices); res = "tai"
        return dices, total, res

    @staticmethod
    def play_chanle(choice):
        num = random.randint(0, 9)
        res = "chan" if num % 2 == 0 else "le"
        return num, res

    @staticmethod
    def play_baucua(choices):
        icons = ["🦀", "🦞", "🐟", "🎲", "🦌", "🐔"]
        results = [random.choice(icons) for _ in range(3)]
        win_count = sum(1 for r in results if r in choices)
        return results, win_count

# ==========================================
# 🎨 GIAO DIỆN UI/UX MULTI-MENU
# ==========================================
def main_menu():
    return ReplyKeyboardMarkup([
        [KeyboardButton("🎲 TÀI XỈU VIP"), KeyboardButton("⚖️ CHẴN LẺ MSB")],
        [KeyboardButton("🦀 BẦU CUA"), KeyboardButton("🎡 VÒNG QUAY")],
        [KeyboardButton("💰 NẠP TIỀN"), KeyboardButton("💸 RÚT TIỀN")],
        [KeyboardButton("🎯 NHIỆM VỤ"), KeyboardButton("🏆 TOP BXH")],
        [KeyboardButton("👤 CÁ NHÂN"), KeyboardButton("🤝 ĐẠI LÝ")],
        [KeyboardButton("🎁 GIFTCODE"), KeyboardButton("⚙️ ADMIN")]
    ], resize_keyboard=True)

# ==========================================
# 📩 CORE HANDLERS - XỬ LÝ LOGIC CHI TIẾT
# ==========================================
def start(update: Update, context: CallbackContext):
    uid = update.effective_user.id
    name = update.effective_user.first_name
    
    # Check ban
    check = db.query("SELECT is_banned FROM users WHERE uid = %s", (uid,))
    if check and check[0]['is_banned']:
        return update.message.reply_text("🚫 Bạn đã bị cấm khỏi hệ thống!")

    # Ref xử lý
    ref_by = 0
    if context.args:
        try:
            r_id = int(context.args[0])
            if r_id != uid: ref_by = r_id
        except: pass

    if not db.query("SELECT * FROM users WHERE uid = %s", (uid,)):
        db.query("INSERT INTO users (uid, username, ref_by) VALUES (%s, %s, %s)", (uid, name, ref_by), fetch=False)
        if ref_by != 0:
            try: context.bot.send_message(ref_by, f"🎊 Bạn nhận được 1 cấp dưới mới: {name}!")
            except: pass

    welcome = (
        f"🔥 **CHÀO MỪNG ĐẠI GIA ĐẾN VỚI TRUMTX** 🔥\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"👋 Xin chào: **{name}**\n"
        f"🆔 ID của bạn: `{uid}`\n"
        f"💰 Số dư: `{db.query('SELECT balance FROM users WHERE uid=%s',(uid,))[0]['balance']:,.0f}đ`\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🚀 Hệ thống nạp rút tự động, uy tín 100%.\n"
        f"🎮 Đa dạng trò chơi, xanh chín nhất Telegram!"
    )
    update.message.reply_text(welcome, reply_markup=main_menu(), parse_mode=ParseMode.MARKDOWN)

def on_text(update: Update, context: CallbackContext):
    uid = update.effective_user.id
    text = update.message.text
    user = db.query("SELECT * FROM users WHERE uid = %s", (uid,))[0]

    if text == "🎲 TÀI XỈU VIP":
        msg = f"🎲 **TÀI XỈU SUPREME**\n💰 Số dư: `{user['balance']:,.0f}đ`\nChọn cửa đặt (x1.95):"
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔴 TÀI", callback_data="tx_tai"), InlineKeyboardButton("⚫ XỈU", callback_data="tx_xiu")],
            [InlineKeyboardButton("💵 10K", callback_data="set_10000"), InlineKeyboardButton("💵 50K", callback_data="set_50000"), InlineKeyboardButton("💵 200K", callback_data="set_200000")],
            [InlineKeyboardButton("🔥 TẤT TAY", callback_data="set_all")]
        ])
        update.message.reply_text(msg, reply_markup=kb, parse_mode=ParseMode.MARKDOWN)

    elif text == "💰 NẠP TIỀN":
        msg = (
            f"🏦 **NẠP TIỀN TỰ ĐỘNG (MSB)**\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"🏧 Ngân hàng: **{BANK_NAME}**\n"
            f"🔢 Số tài khoản: `{BANK_ACC}`\n"
            f"👤 Chủ TK: **{BANK_USER}**\n"
            f"📝 Nội dung nạp: `{uid}`\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"⚠️ **LƯU Ý:** Ghi đúng ID `{uid}`. Tiền cộng sau 30s-1p!"
        )
        update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)

    elif text == "💸 RÚT TIỀN":
        if not user['bank_acc']:
            update.message.reply_text("❌ Bạn chưa liên kết ngân hàng!\nCú pháp: `/link [STK] [TEN_BANK] [TEN_CHU_TK]`")
        else:
            msg = (f"💸 **LỆNH RÚT TIỀN**\n💰 Số dư: `{user['balance']:,.0f}đ`\n"
                   f"🏦 Bank: `{user['bank_name']} - {user['bank_acc']}`\n"
                   f"👉 Cú pháp: `/rut [số_tiền]`")
            update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)

    elif text == "🎯 NHIỆM VỤ":
        bet = user['total_bet']
        m1 = "✅" if bet >= 500000 else "❌"
        m2 = "✅" if bet >= 5000000 else "❌"
        msg = (f"🎯 **NHIỆM VỤ ĐẠI GIA**\n\n"
               f"{m1} Cược tổng 500k: Thưởng 10k\n"
               f"{m2} Cược tổng 5M: Thưởng 100k\n"
               f"━━━━━━━━━━━━━━━━━━━━\n"
               f"📊 Tổng cược của bạn: `{bet:,.0f}đ`")
        update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)

    elif text == "👤 CÁ NHÂN":
        msg = (f"👤 **THÔNG TIN CÁ NHÂN**\n━━━━━━━━━━━━━━━━━━━━\n"
               f"🆔 ID: `{uid}`\n"
               f"💰 Số dư: `{user['balance']:,.0f}đ`\n"
               f"📊 Tổng cược: `{user['total_bet']:,.0f}đ`\n"
               f"🏆 Tổng thắng: `{user['total_win']:,.0f}đ`\n"
               f"🤝 Hoa hồng: `{user['total_ref_earn']:,.0f}đ`\n"
               f"🏦 Bank: `{user['bank_name']} | {user['bank_acc']}`")
        update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)

    elif text == "⚙️ ADMIN" and uid == ADMIN_ID:
        kb = [
            [KeyboardButton("📊 THỐNG KÊ"), KeyboardButton("📢 THÔNG BÁO ALL")],
            [KeyboardButton("💳 CỘNG TIỀN"), KeyboardButton("🚫 KHÓA USER")],
            [KeyboardButton("🏠 QUAY LẠI")]
        ]
        update.message.reply_text("🛠 **MENU QUẢN TRỊ VIÊN**", reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True))

# ==========================================
# 🎮 CALLBACK HANDLERS - XỬ LÝ ĐẶT CƯỢC
# ==========================================
bet_storage = {}

def handle_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    uid = query.from_user.id
    data = query.data
    user = db.query("SELECT * FROM users WHERE uid = %s", (uid,))[0]

    if data.startswith("set_"):
        amt = data.split("_")[1]
        bet_storage[uid] = user['balance'] if amt == "all" else int(amt)
        query.answer(f"✅ Đã chọn cược: {bet_storage[uid]:,.0f}đ")

    elif data.startswith("tx_"):
        choice = data.split("_")[1]
        bet = bet_storage.get(uid, 10000)
        
        if user['balance'] < bet: 
            return query.answer("❌ Số dư không đủ!", show_alert=True)
        if bet < 1000:
            return query.answer("❌ Cược tối thiểu 1,000đ!", show_alert=True)

        # Trừ tiền & Tính hoa hồng
        db.query("UPDATE users SET balance = balance - %s, total_bet = total_bet + %s WHERE uid = %s", (bet, bet, uid), fetch=False)
        if user['ref_by'] != 0:
            comm = bet * 0.05
            db.query("UPDATE users SET balance = balance + %s, total_ref_earn = total_ref_earn + %s WHERE uid = %s", (comm, comm, user['ref_by']), fetch=False)

        # Chạy Game
        wr = db.query("SELECT value FROM admin_config WHERE key='win_rate'")[0]['value']
        dices, total, res = GameEngine.play_taixiu(choice, wr)

        if choice == res:
            win_amt = bet * 1.95
            db.query("UPDATE users SET balance = balance + %s, total_win = total_win + %s WHERE uid = %s", (win_amt, win_amt, uid), fetch=False)
            result_msg = (f"🎉 **CHIẾN THẮNG!**\n"
                          f"🎲 Kết quả: {dices[0]}-{dices[1]}-{dices[2]} = {total} ({res.upper()})\n"
                          f"💰 Nhận: `+{win_amt:,.0f}đ`\n"
                          f"💰 Số dư: `{user['balance'] - bet + win_amt:,.0f}đ`")
        else:
            result_msg = (f"❌ **THẤT BẠI!**\n"
                          f"🎲 Kết quả: {dices[0]}-{dices[1]}-{dices[2]} = {total} ({res.upper()})\n"
                          f"💸 Mất: `-{bet:,.0f}đ`\n"
                          f"💰 Số dư: `{user['balance'] - bet:,.0f}đ`")
        
        query.edit_message_text(result_msg, reply_markup=query.message.reply_markup, parse_mode=ParseMode.MARKDOWN)

# ==========================================
# 🛠 LỆNH TIỆN ÍCH & ADMIN COMMANDS
# ==========================================
def link_bank(update: Update, context: CallbackContext):
    try:
        args = context.args
        db.query("UPDATE users SET bank_acc=%s, bank_name=%s, bank_user=%s WHERE uid=%s", 
                 (args[0], args[1], " ".join(args[2:]).upper(), update.effective_user.id), fetch=False)
        update.message.reply_text("✅ Đã liên kết ngân hàng thành công!")
    except:
        update.message.reply_text("⚠️ Sai cú pháp! Ví dụ: `/link 123456789 MSB NGUYEN VAN A`")

def withdraw(update: Update, context: CallbackContext):
    uid = update.effective_user.id
    amt = float(context.args[0])
    user = db.query("SELECT balance FROM users WHERE uid = %s", (uid,))[0]
    
    if user['balance'] < amt: return update.message.reply_text("❌ Số dư không đủ!")
    if amt < 50000: return update.message.reply_text("❌ Rút tối thiểu 50,000đ!")

    db.query("UPDATE users SET balance = balance - %s WHERE uid = %s", (amt, uid), fetch=False)
    db.query("INSERT INTO withdraw_requests (uid, amount) VALUES (%s, %s)", (uid, amt), fetch=False)
    
    # Gửi thông báo cho Admin
    admin_kb = InlineKeyboardMarkup([[InlineKeyboardButton("✅ DUYỆT", callback_data=f"approve_{uid}_{amt}")]])
    context.bot.send_message(ADMIN_ID, f"🔔 **LỆNH RÚT MỚI**\nID: `{uid}`\nSố tiền: `{amt:,.0f}đ`", reply_markup=admin_kb)
    update.message.reply_text("✅ Đã gửi lệnh rút, vui lòng chờ Admin duyệt!")

# ==========================================
# 🚀 KHỞI CHẠY HỆ THỐNG
# ==========================================
if __name__ == '__main__':
    # Chạy Web Server chống ngủ
    threading.Thread(target=run_flask, daemon=True).start()
    
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    # Đăng ký Handlers
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("link", link_bank))
    dp.add_handler(CommandHandler("rut", withdraw))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, on_text))
    dp.add_handler(CallbackQueryHandler(handle_callback))
    
    print("🚀 TRUMTX SUPREME V5 - FULL SYSTEM READY!")
    updater.start_polling(drop_pending_updates=True)
    updater.idle()
    
