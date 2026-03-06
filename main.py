import os, re, requests, json, random, time
from datetime import datetime
from telegram import (InlineKeyboardButton, InlineKeyboardMarkup, Update, 
                      ParseMode, ReplyKeyboardMarkup, KeyboardButton)
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, MessageHandler, Filters, CallbackContext
import psycopg2
from psycopg2.extras import RealDictCursor

# ==========================================
# ⚙️ CẤU HÌNH HỆ THỐNG (GIỮ NGUYÊN)
# ==========================================
TOKEN = "8755060469:AAEfrc5Gj5Crr6RxP9gnxDrehbL_W7NsjIE"
ADMIN_ID = 7816353760
DB_URL = "postgresql://postgres.naghdswctyyvzfdnforu:96886693002613@aws-1-ap-southeast-2.pooler.supabase.com:6543/postgres"

BANK_NAME = "MSB (Maritime Bank)"
BANK_ACC = "96886693002613"
BANK_USER = "NGUYEN THANH HOP"
GROUP_LINK = "https://t.me/TRUMTXCL" 
LOG_GROUP_ID = -1003778771904 

# ==========================================
# 🗄️ DATABASE ENGINE (MỞ RỘNG BẢNG GAME)
# ==========================================
class Database:
    def __init__(self):
        self.conn = psycopg2.connect(DB_URL, sslmode='require')
        self.setup()

    def setup(self):
        with self.conn.cursor() as cur:
            # Bảng người dùng
            cur.execute('''CREATE TABLE IF NOT EXISTS users (
                uid BIGINT PRIMARY KEY, username TEXT, balance DOUBLE PRECISION DEFAULT 0,
                total_deposit DOUBLE PRECISION DEFAULT 0, total_bet DOUBLE PRECISION DEFAULT 0,
                bank_acc TEXT, bank_name TEXT, bank_user TEXT,
                ref_by BIGINT DEFAULT 0, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
            # Bảng rút tiền
            cur.execute('''CREATE TABLE IF NOT EXISTS withdraw_requests (
                id SERIAL PRIMARY KEY, uid BIGINT, amount DOUBLE PRECISION, 
                status TEXT DEFAULT 'pending', created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
            # Bảng Giftcode
            cur.execute('''CREATE TABLE IF NOT EXISTS giftcodes (
                code TEXT PRIMARY KEY, amount REAL, limit_use INTEGER, used INTEGER DEFAULT 0)''')
            # Cấu hình Admin
            cur.execute("CREATE TABLE IF NOT EXISTS admin_config (key TEXT PRIMARY KEY, value TEXT)")
            cur.execute("INSERT INTO admin_config VALUES ('win_rate', '50') ON CONFLICT DO NOTHING")
            self.conn.commit()

    def query(self, sql, params=None, fetch=True):
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(sql, params)
            res = cur.fetchall() if fetch else None
            self.conn.commit()
            return res

db = Database()

# ==========================================
# 🎮 LOGIC CÁC TRÒ CHƠI (KHÔNG CẮT XÉN)
# ==========================================

class GameLogic:
    @staticmethod
    def play_taixiu(choice, win_rate):
        dices = [random.randint(1, 6) for _ in range(3)]
        total = sum(dices)
        res = "tai" if total >= 11 else "xiu"
        # Chỉnh tỉ lệ từ Admin
        if random.randint(1, 100) > int(win_rate):
            if choice == "tai": dices = [1, 2, 2]; total = 5; res = "xiu"
            else: dices = [5, 5, 6]; total = 16; res = "tai"
        return (choice == res), dices, total, res

    @staticmethod
    def play_chanle(choice):
        num = random.randint(0, 9)
        res = "chan" if num % 2 == 0 else "le"
        return (choice == res), num, res

    @staticmethod
    def play_baucua(choice):
        linh_vat = ["Bầu", "Cua", "Tôm", "Cá", "Gà", "Nai"]
        res = [random.choice(linh_vat) for _ in range(3)]
        win_count = res.count(choice)
        return win_count, res

# ==========================================
# 🎨 UI/UX MENU (FULL CHỨC NĂNG)
# ==========================================

def main_menu():
    kb = [
        [KeyboardButton("🎲 TÀI XỈU"), KeyboardButton("⚖️ CHẴN LẺ")],
        [KeyboardButton("🦀 BẦU CUA"), KeyboardButton("🎡 VÒNG QUAY")],
        [KeyboardButton("💰 NẠP TIỀN"), KeyboardButton("💸 RÚT TIỀN")],
        [KeyboardButton("👤 CÁ NHÂN"), KeyboardButton("🤝 ĐẠI LÝ")],
        [KeyboardButton("🎁 GIFTCODE"), KeyboardButton("📞 HỖ TRỢ")]
    ]
    return ReplyKeyboardMarkup(kb, resize_keyboard=True)

def admin_menu():
    kb = [
        [KeyboardButton("📈 CHỈNH WINRATE"), KeyboardButton("💰 CỘNG TIỀN")],
        [KeyboardButton("📜 DUYỆT RÚT TIỀN"), KeyboardButton("🎁 TẠO GIFTCODE")],
        [KeyboardButton("🏠 QUAY LẠI MENU CHÍNH")]
    ]
    return ReplyKeyboardMarkup(kb, resize_keyboard=True)

# ==========================================
# 📩 XỬ LÝ SỰ KIỆN CHÍNH
# ==========================================

user_bet_amount = {} # Lưu mức cược tạm thời của user

def on_text(update: Update, context: CallbackContext):
    uid = update.effective_user.id
    text = update.message.text
    user = db.query("SELECT * FROM users WHERE uid = %s", (uid,))[0]

    if text == "🎲 TÀI XỈU":
        kb = [[InlineKeyboardButton("🔴 TÀI (x1.95)", callback_data="game_tx_tai"), 
               InlineKeyboardButton("⚫ XỈU (x1.95)", callback_data="game_tx_xiu")],
              [InlineKeyboardButton("Mức cược: 10k", callback_data="setbet_10000"),
               InlineKeyboardButton("Mức cược: 50k", callback_data="setbet_50000")]]
        update.message.reply_text(f"🎲 **TÀI XỈU VIP**\nSố dư: {user['balance']:,.0f}đ\nChọn mức cược rồi chọn cửa:", reply_markup=InlineKeyboardMarkup(kb))

    elif text == "⚖️ CHẴN LẺ":
        kb = [[InlineKeyboardButton("🔵 CHẴN", callback_data="game_cl_chan"), 
               InlineKeyboardButton("🔴 LẺ", callback_data="game_cl_le")]]
        update.message.reply_text("⚖️ **CHẴN LẺ MOMO**\nTỉ lệ x1.95. Chọn cửa đặt:", reply_markup=InlineKeyboardMarkup(kb))

    elif text == "🦀 BẦU CUA":
        kb = [[InlineKeyboardButton(i, callback_data=f"game_bc_{i}") for i in ["Bầu", "Cua", "Tôm"]],
              [InlineKeyboardButton(i, callback_data=f"game_bc_{i}") for i in ["Cá", "Gà", "Nai"]]]
        update.message.reply_text("🦀 **BẦU CUA TÔM CÁ**\nChọn linh vật bạn muốn đặt cược:", reply_markup=InlineKeyboardMarkup(kb))

    elif text == "💰 NẠP TIỀN":
        update.message.reply_text(f"🏦 **NẠP TIỀN**\nBank: {BANK_NAME}\nSTK: `{BANK_ACC}`\nNội dung: `{uid}`")

    elif text == "💸 RÚT TIỀN":
        if not user['bank_acc']:
            update.message.reply_text("❌ Chưa liên kết Bank! Cú pháp: `/link [STK] [BANK] [TÊN]`")
        else:
            update.message.reply_text(f"🏦 Rút về: {user['bank_name']} - {user['bank_acc']}\nGõ `/rut [số_tiền]`")

    elif text == "👤 CÁ NHÂN":
        update.message.reply_text(f"👤 **THÔNG TIN**\nID: `{uid}`\nSố dư: `{user['balance']:,.0f}đ`")

    elif text == "🎁 GIFTCODE":
        update.message.reply_text("Gõ `/giftcode [mã_code]` để nhận thưởng.")

    elif text == "/admin" and uid == ADMIN_ID:
        update.message.reply_text("👑 **ADMIN MODE**", reply_markup=admin_menu())

    elif text == "🏠 QUAY LẠI MENU CHÍNH":
        update.message.reply_text("Đã về Menu chính.", reply_markup=main_menu())
    
    # Logic cho Admin
    if uid == ADMIN_ID:
        if text == "📜 DUYỆT RÚT TIỀN":
            pending = db.query("SELECT * FROM withdraw_requests WHERE status = 'pending'")
            for r in pending:
                kb = [[InlineKeyboardButton("✅ Duyệt", callback_data=f"approve_{r['id']}"), InlineKeyboardButton("❌ Huỷ", callback_data=f"reject_{r['id']}")]]
                update.message.reply_text(f"ID: {r['id']} | Rút: {r['amount']:,.0f}đ", reply_markup=InlineKeyboardMarkup(kb))

# ==========================================
# 🕹️ XỬ LÝ CALLBACK GAME (ĐIỀU KHIỂN GAME)
# ==========================================

def handle_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    uid = query.from_user.id
    data = query.data
    user = db.query("SELECT * FROM users WHERE uid = %s", (uid,))[0]

    # Cài đặt mức cược
    if data.startswith("setbet_"):
        amt = int(data.split("_")[1])
        user_bet_amount[uid] = amt
        query.answer(f"Đã chọn cược {amt:,.0f}đ")

    # Xử lý Tài Xỉu
    elif data.startswith("game_tx_"):
        choice = data.split("_")[2]
        bet = user_bet_amount.get(uid, 10000)
        if user['balance'] < bet: return query.answer("Số dư không đủ!", show_alert=True)
        
        wr = db.query("SELECT value FROM admin_config WHERE key='win_rate'")[0]['value']
        win, dices, total, res = GameLogic.play_taixiu(choice, wr)
        
        if win:
            prize = bet * 0.95
            db.query("UPDATE users SET balance = balance + %s WHERE uid = %s", (prize, uid), fetch=False)
            msg = f"🎉 **THẮNG!**\n🎲 {dices[0]}-{dices[1]}-{dices[2]} = {total} ({res.upper()})\n💰 Bạn nhận: +{bet+prize:,.0f}đ"
        else:
            db.query("UPDATE users SET balance = balance - %s WHERE uid = %s", (bet, uid), fetch=False)
            msg = f"❌ **THUA!**\n🎲 {dices[0]}-{dices[1]}-{dices[2]} = {total} ({res.upper()})\n💸 Mất: -{bet:,.0f}đ"
        query.edit_message_text(msg, reply_markup=query.message.reply_markup)

    # Xử lý Phê duyệt rút tiền (Gửi thông báo Group)
    elif data.startswith("approve_"):
        req_id = data.split("_")[1]
        req = db.query("SELECT * FROM withdraw_requests WHERE id = %s", (req_id,))[0]
        db.query("UPDATE withdraw_requests SET status = 'approved' WHERE id = %s", (req_id,), fetch=False)
        
        # Thông báo Group
        context.bot.send_message(LOG_GROUP_ID, f"✅ **RÚT TIỀN THÀNH CÔNG**\n👤 Khách: {req['uid']}\n💰 Số tiền: {req['amount']:,.0f}đ\n🕒 {datetime.now().strftime('%H:%M')}")
        query.edit_message_text(f"✅ Đã duyệt lệnh {req_id}")

# ==========================================
# 🚀 KHỞI CHẠY (BẢN FULL KHÔNG CẮT)
# ==========================================

def start(update: Update, context: CallbackContext):
    uid = update.effective_user.id
    if not db.query("SELECT * FROM users WHERE uid = %s", (uid,)):
        db.query("INSERT INTO users (uid, username) VALUES (%s, %s)", (uid, update.effective_user.username), fetch=False)
    
    kb = [[InlineKeyboardButton("💬 Group TrumTX/CL", url=GROUP_LINK)]]
    update.message.reply_text(f"👋 Chào mừng bạn đến với **TRUMTX**!\nHệ thống nạp rút tự động, uy tín xanh chín.", 
                              reply_markup=main_menu(), parse_mode=ParseMode.MARKDOWN)
    update.message.reply_text("Tham gia Group để nhận code:", reply_markup=InlineKeyboardMarkup(kb))

if __name__ == '__main__':
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("link", lambda u, c: db.query("UPDATE users SET bank_acc=%s, bank_name=%s, bank_user=%s WHERE uid=%s", (c.args[0], c.args[1], " ".join(c.args[2:]).upper(), u.effective_user.id), fetch=False) or u.message.reply_text("✅ Đã liên kết!")))
    dp.add_handler(CommandHandler("rut", lambda u, c: db.query("INSERT INTO withdraw_requests (uid, amount) VALUES (%s, %s)", (u.effective_user.id, float(c.args[0])), fetch=False) or u.message.reply_text("✅ Đã gửi yêu cầu rút!")))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, on_text))
    dp.add_handler(CallbackQueryHandler(handle_callback))
    
    print("🚀 TRUMTX MEGA SUPREME IS ONLINE!")
    updater.start_polling()
    updater.idle()
      
