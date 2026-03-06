import os, re, requests, json, random, time
from datetime import datetime
from threading import Thread
from telegram import (InlineKeyboardButton, InlineKeyboardMarkup, Update, 
                      ParseMode, ReplyKeyboardMarkup, KeyboardButton)
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, MessageHandler, Filters, CallbackContext
import psycopg2
from psycopg2.extras import RealDictCursor

# ==========================================
# ⚙️ HỆ THỐNG CẤU HÌNH BIẾN
# ==========================================
TOKEN = "8755060469:AAEfrc5Gj5Crr6RxP9gnxDrehbL_W7NsjIE"
ADMIN_ID = 7816353760
DB_URL = "postgresql://postgres.naghdswctyyvzfdnforu:96886693002613@aws-1-ap-southeast-2.pooler.supabase.com:6543/postgres"

# Game Settings
TAX = 0.05
MIN_RUT = 50000

# ==========================================
# 🗄️ DATABASE QUẢN LÝ TẬP TRUNG
# ==========================================
class CoreDB:
    def __init__(self):
        self.conn = psycopg2.connect(DB_URL, sslmode='require')
        self.init_tables()

    def init_tables(self):
        with self.conn.cursor() as cur:
            # Người dùng & Đại lý
            cur.execute('''CREATE TABLE IF NOT EXISTS users (
                uid BIGINT PRIMARY KEY, username TEXT, balance DOUBLE PRECISION DEFAULT 0,
                total_nap DOUBLE PRECISION DEFAULT 0, total_cuoc DOUBLE PRECISION DEFAULT 0,
                ref_by BIGINT DEFAULT 0, status TEXT DEFAULT 'active')''')
            # Lịch sử biến động số dư (Quan trọng để check log)
            cur.execute('''CREATE TABLE IF NOT EXISTS balance_logs (
                id SERIAL PRIMARY KEY, uid BIGINT, amount DOUBLE PRECISION, 
                reason TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
            # Lịch sử Game
            cur.execute('''CREATE TABLE IF NOT EXISTS game_results (
                id SERIAL PRIMARY KEY, game_type TEXT, result TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
            # Cấu hình Admin
            cur.execute("CREATE TABLE IF NOT EXISTS admin_config (key TEXT PRIMARY KEY, value TEXT)")
            cur.execute("INSERT INTO admin_config VALUES ('win_rate', '50'), ('maintenance', 'off') ON CONFLICT DO NOTHING")
            self.conn.commit()

    def exec(self, sql, params=None, fetch=False):
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(sql, params)
            if fetch: return cur.fetchall()
            self.conn.commit()

db = CoreDB()

# ==========================================
# 🛠️ ADMIN CONTROL PANEL (DÀNH RIÊNG CHO BẠN)
# ==========================================
def admin_menu(update, context):
    if update.effective_user.id != ADMIN_ID: return
    
    stats = db.exec("SELECT COUNT(*) as users, SUM(balance) as vault FROM users", fetch=True)[0]
    wr = db.exec("SELECT value FROM admin_config WHERE key = 'win_rate'", fetch=True)[0]['value']
    
    txt = (f"👑 **HỆ THỐNG QUẢN TRỊ ADMIN**\n"
           f"────────────────────\n"
           f"👥 Tổng khách: `{stats['users']}`\n"
           f"💰 Tổng quỹ ví: `{stats['vault'] or 0:,.0f}đ`\n"
           f"📈 Tỉ lệ thắng hiện tại: `{wr}%`\n"
           f"────────────────────\n"
           f"🛠 **Lệnh điều khiển:**\n"
           f"1️⃣ `/addmoney [ID] [Số_tiền]` - Cộng tiền\n"
           f"2️⃣ `/submoney [ID] [Số_tiền]` - Trừ tiền\n"
           f"3️⃣ `/setwin [Phần_trăm]` - Chỉnh tỉ lệ thắng\n"
           f"4️⃣ `/ban [ID]` - Khóa tài khoản\n"
           f"5️⃣ `/check [ID]` - Soi lịch sử cược")
    update.message.reply_text(txt, parse_mode=ParseMode.MARKDOWN)

def admin_actions(update, context):
    if update.effective_user.id != ADMIN_ID: return
    cmd = update.message.text.split()
    try:
        if "/addmoney" in cmd:
            uid, amt = int(cmd[1]), float(cmd[2])
            db.exec("UPDATE users SET balance = balance + %s WHERE uid = %s", (amt, uid))
            db.exec("INSERT INTO balance_logs (uid, amount, reason) VALUES (%s, %s, %s)", (uid, amt, "Admin cộng tiền"))
            update.message.reply_text(f"✅ Đã cộng {amt:,.0f}đ cho ID {uid}")
        
        elif "/setwin" in cmd:
            rate = cmd[1]
            db.exec("UPDATE admin_config SET value = %s WHERE key = 'win_rate'", (rate,))
            update.message.reply_text(f"✅ Đã chỉnh tỉ lệ thắng hệ thống thành {rate}%")
    except Exception as e: update.message.reply_text(f"Lỗi: {str(e)}")

# ==========================================
# 🎲 HỆ THỐNG ĐA TRÒ CHƠI (MULTI-GAMES)
# ==========================================

# 1. Logic Tài Xỉu
def play_taixiu(uid, bet_amt, choice):
    # Check Win Rate
    win_rate = int(db.exec("SELECT value FROM admin_config WHERE key = 'win_rate'", fetch=True)[0]['value'])
    dices = [random.randint(1,6) for _ in range(3)]
    total = sum(dices)
    res = "tai" if total >= 11 else "xiu"
    
    # Can thiệp tỉ lệ
    if random.randint(1, 100) > win_rate:
        if choice == "tai": dices = [1, 2, 2]; total = 5; res = "xiu"
        else: dices = [5, 5, 6]; total = 16; res = "tai"

    is_win = (choice == res)
    return is_win, dices, total, res

# 2. Logic Bầu Cua
def play_baucua(uid, bet_amt, choice):
    items = ["Bầu", "Cua", "Tôm", "Cá", "Gà", "Nai"]
    results = [random.choice(items) for _ in range(3)]
    match_count = results.count(choice)
    return match_count, results

# ==========================================
# 📩 XỬ LÝ GIAO DIỆN & TIN NHẮN
# ==========================================
def main_menu():
    return ReplyKeyboardMarkup([
        [KeyboardButton("🎲 TÀI XỈU"), KeyboardButton("🦀 BẦU CUA")],
        [KeyboardButton("⚖️ CHẴN LẺ"), KeyboardButton("🎡 VÒNG QUAY")],
        [KeyboardButton("🏦 NẠP/RÚT"), KeyboardButton("👤 CÁ NHÂN")],
        [KeyboardButton("🤝 ĐẠI LÝ"), KeyboardButton("🏆 TOP BXH")]
    ], resize_keyboard=True)

def handle_message(update, context):
    uid = update.effective_user.id
    text = update.message.text
    user = db.exec("SELECT * FROM users WHERE uid = %s", (uid,), fetch=True)[0]

    if text == "🎲 TÀI XỈU":
        kb = [[InlineKeyboardButton("🔴 TÀI", callback_data="tx_tai"), InlineKeyboardButton("⚫ XỈU", callback_data="tx_xiu")],
              [InlineKeyboardButton("10k", callback_data="set_10"), InlineKeyboardButton("50k", callback_data="set_50"), InlineKeyboardButton("Hết tay", callback_data="set_all")]]
        update.message.reply_text(f"🎲 **SÒNG TÀI XỈU VIP**\nSố dư: `{user['balance']:,.0f}đ`\nChọn mức cược và cửa:", reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.MARKDOWN)

    elif text == "🦀 BẦU CUA":
        kb = [[InlineKeyboardButton(i, callback_data=f"bc_{i}") for i in ["Bầu", "Cua", "Tôm"]],
              [InlineKeyboardButton(i, callback_data=f"bc_{i}") for i in ["Cá", "Gà", "Nai"]]]
        update.message.reply_text("🦀 **BẦU CUA TÔM CÁ**\nĐặt 1 được 3, chọn linh vật của bạn:", reply_markup=InlineKeyboardMarkup(kb))

    elif text == "🏦 NẠP/RÚT":
        txt = (f"💳 **QUẢN LÝ TÀI CHÍNH**\n"
               f"Số dư: `{user['balance']:,.0f}đ`\n"
               f"Nạp tiền: Chuyển khoản MSB nội dung `{uid}`\n"
               f"Rút tiền: `/rut [Số_tiền] [STK] [Ngân_hàng]`")
        update.message.reply_text(txt, parse_mode=ParseMode.MARKDOWN)

# ==========================================
# ⚙️ CALLBACK GAME ENGINE
# ==========================================
user_bet_tmp = {} # Lưu mức cược người dùng {uid: amount}

def callback_handler(update, context):
    query = update.callback_query
    uid = query.from_user.id
    data = query.data
    user = db.exec("SELECT * FROM users WHERE uid = %s", (uid,), fetch=True)[0]

    if data.startswith("set_"):
        amt = data.split("_")[1]
        user_bet_tmp[uid] = user['balance'] if amt == "all" else int(amt)*1000
        query.answer(f"Đã chọn mức cược: {user_bet_tmp[uid]:,.0f}đ")
        
    elif data.startswith("tx_"):
        choice = data.split("_")[1]
        bet = user_bet_tmp.get(uid, 10000)
        if user['balance'] < bet: return query.answer("Số dư không đủ!", show_alert=True)
        
        win, ds, total, res = play_taixiu(uid, bet, choice)
        if win:
            prize = bet * (2 - TAX)
            db.exec("UPDATE users SET balance = balance + %s WHERE uid = %s", (prize - bet, uid))
            msg = f"✅ **THẮNG RỰC RỠ**\n🎲 `{ds[0]}+{ds[1]}+{ds[2]} = {total}` ({res.upper()})\n💰 Nhận: `+{prize:,.0f}đ`"
        else:
            db.exec("UPDATE users SET balance = balance - %s WHERE uid = %s", (bet, uid))
            msg = f"❌ **THUA RỒI**\n🎲 `{ds[0]}+{ds[1]}+{ds[2]} = {total}` ({res.upper()})\n💸 Mất: `-{bet:,.0f}đ`"
        query.edit_message_text(msg, reply_markup=query.message.reply_markup, parse_mode=ParseMode.MARKDOWN)

# ==========================================
# 🚀 KHỞI CHẠY HỆ THỐNG
# ==========================================
def start(update, context):
    uid = update.effective_user.id
    if not db.exec("SELECT * FROM users WHERE uid = %s", (uid,), fetch=True):
        db.exec("INSERT INTO users (uid, username) VALUES (%s, %s)", (uid, update.effective_user.username))
    update.message.reply_text("💎 **TRUMTX SUPREME v2**\nHệ thống Casino uy tín số 1 Telegram.", reply_markup=main_menu())

if __name__ == '__main__':
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("admin", admin_menu))
    dp.add_handler(MessageHandler(Filters.regex(r'^/'), admin_actions)) # Xử lý các lệnh admin /addmoney, /setwin...
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))
    dp.add_handler(CallbackQueryHandler(callback_handler))
    
    print("🚀 SERVER IS LIVE!")
    updater.start_polling()
    updater.idle()
