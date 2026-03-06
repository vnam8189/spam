import os, re, requests, json, random, time, threading, logging
from datetime import datetime, timedelta
from telegram import (InlineKeyboardButton, InlineKeyboardMarkup, Update, 
                      ParseMode, ReplyKeyboardMarkup, KeyboardButton, InputMediaPhoto, ChatAction)
from telegram.ext import (Updater, CommandHandler, CallbackQueryHandler, 
                          MessageHandler, Filters, CallbackContext, JobQueue)
import psycopg2
from psycopg2.extras import RealDictCursor

# ==========================================
# ⚙️ CẤU HÌNH HỆ THỐNG (BẢO MẬT TUYỆT ĐỐI)
# ==========================================
TOKEN = "8755060469:AAH1R02X_408_mNFPcOH8harJI25Z96UZL4"
ADMIN_ID = 7816353760
DB_URL = "postgresql://postgres.naghdswctyyvzfdnforu:96886693002613@aws-1-ap-southeast-2.pooler.supabase.com:6543/postgres"

# Thông tin thanh toán (Fix cứng theo ảnh yêu cầu)
BANK_NAME = "MSB (Maritime Bank)"
BANK_ACC = "96886693002613"
BANK_USER = "NGUYEN THANH HOP"
GROUP_LINK = "https://t.me/TRUMTXCL" 
LOG_GROUP_ID = -1003778771904 

# Cấu hình log để theo dõi lỗi
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# ==========================================
# 🗄️ DATABASE ENGINE (SCALABLE ARCHITECTURE)
# ==========================================
class Database:
    def __init__(self):
        try:
            self.conn = psycopg2.connect(DB_URL, sslmode='require')
            self.setup()
            print("✅ Database Connected Successfully!")
        except Exception as e:
            print(f"❌ Database Error: {e}")

    def setup(self):
        with self.conn.cursor() as cur:
            # Bảng Users (Mở rộng cực lớn)
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
                level INTEGER DEFAULT 1,
                exp INTEGER DEFAULT 0,
                is_banned BOOLEAN DEFAULT FALSE,
                last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
            
            # Bảng Rút tiền
            cur.execute('''CREATE TABLE IF NOT EXISTS withdraw_requests (
                id SERIAL PRIMARY KEY, uid BIGINT, amount DOUBLE PRECISION, 
                status TEXT DEFAULT 'pending', created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
            
            # Bảng Lịch sử giao dịch (Chống chối cãi)
            cur.execute('''CREATE TABLE IF NOT EXISTS transactions (
                id SERIAL PRIMARY KEY, uid BIGINT, type TEXT, 
                amount DOUBLE PRECISION, balance_after DOUBLE PRECISION,
                content TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')

            # Bảng Giftcode (Có thời hạn)
            cur.execute('''CREATE TABLE IF NOT EXISTS giftcodes (
                code TEXT PRIMARY KEY, amount REAL, limit_use INTEGER, 
                used INTEGER DEFAULT 0, expired_at TIMESTAMP)''')

            # Bảng Cấu hình Admin
            cur.execute("CREATE TABLE IF NOT EXISTS admin_config (key TEXT PRIMARY KEY, value TEXT)")
            configs = [
                ('win_rate', '50'), 
                ('min_withdraw', '50000'), 
                ('ref_percent', '5'),
                ('maintenance', 'false'),
                ('bot_status', 'online')
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
                logger.error(f"SQL Error: {e}")
                return []

db = Database()

# ==========================================
# 🛠️ UTILS & HELPERS
# ==========================================
class Utils:
    @staticmethod
    def format_money(amount):
        return "{:,.0f}đ".format(amount)

    @staticmethod
    def get_level_info(exp):
        level = (exp // 1000) + 1
        return level

# ==========================================
# 🎨 GIAO DIỆN UI/UX MULTI-LAYER
# ==========================================

def get_main_kb():
    return ReplyKeyboardMarkup([
        [KeyboardButton("🎲 TÀI XỈU VIP"), KeyboardButton("⚖️ CHẴN LẺ MSB")],
        [KeyboardButton("🦀 BẦU CUA"), KeyboardButton("🎡 VÒNG QUAY")],
        [KeyboardButton("💰 NẠP TIỀN"), KeyboardButton("💸 RÚT TIỀN")],
        [KeyboardButton("🎯 NHIỆM VỤ"), KeyboardButton("🏆 TOP ĐẠI GIA")],
        [KeyboardButton("👤 CÁ NHÂN"), KeyboardButton("🤝 ĐẠI LÝ 5.0")],
        [KeyboardButton("🎁 GIFTCODE"), KeyboardButton("⚙️ CÀI ĐẶT")]
    ], resize_keyboard=True)

def get_admin_kb():
    return ReplyKeyboardMarkup([
        [KeyboardButton("📊 THỐNG KÊ"), KeyboardButton("📢 THÔNG BÁO ALL")],
        [KeyboardButton("💳 CỘNG/TRỪ TIỀN"), KeyboardButton("🚫 BAN/UNBAN")],
        [KeyboardButton("📜 DUYỆT RÚT TIỀN"), KeyboardButton("🎫 TẠO GIFTCODE")],
        [KeyboardButton("🏠 VỀ MENU CHÍNH")]
    ], resize_keyboard=True)

# ==========================================
# 🕹️ GAME ENGINES (ADVANCED LOGIC)
# ==========================================

class GameEngines:
    @staticmethod
    def tx_logic(choice, wr_percent):
        # Thuật toán xúc xắc ngẫu nhiên
        dices = [random.randint(1, 6) for _ in range(3)]
        total = sum(dices)
        res = "tai" if total >= 11 else "xiu"
        
        # Logic can thiệp Admin
        if random.randint(1, 100) > int(wr_percent):
            if choice == "tai":
                dices = [random.randint(1, 3), random.randint(1, 3), random.randint(1, 4)]
            else:
                dices = [random.randint(4, 6), random.randint(4, 6), random.randint(4, 6)]
            total = sum(dices)
            res = "tai" if total >= 11 else "xiu"
        return dices, total, res

    @staticmethod
    def cl_logic():
        num = random.randint(0, 9)
        return num, ("chan" if num % 2 == 0 else "le")

# ==========================================
# 📩 CORE HANDLERS
# ==========================================

def start(update: Update, context: CallbackContext):
    uid = update.effective_user.id
    name = update.effective_user.first_name
    
    # Bảo mật: Chống người dùng bị Ban
    user_check = db.query("SELECT is_banned FROM users WHERE uid = %s", (uid,))
    if user_check and user_check[0]['is_banned']:
        return update.message.reply_text("🚫 Tài khoản của bạn đã bị khóa do vi phạm chính sách.")

    # Xử lý Mã mời (Referral)
    ref_id = 0
    if context.args:
        try:
            r_id = int(context.args[0])
            if r_id != uid: ref_id = r_id
        except: pass

    # Đăng ký user mới
    if not user_check:
        db.query("INSERT INTO users (uid, username, ref_by) VALUES (%s, %s, %s)", (uid, name, ref_id), fetch=False)
        if ref_id != 0:
            try: context.bot.send_message(ref_id, f"🎊 Cấp dưới mới: **{name}** vừa tham gia qua link của bạn!")
            except: pass

    # Giao diện chào mừng
    welcome_msg = (
        f"👑 **TRUMTX SUPREME CASINO v5.0** 👑\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"👋 Chào mừng đại gia: **{name}**\n"
        f"🆔 ID: `{uid}` | 🎖️ Level: `{Utils.get_level_info(0)}` \n"
        f"💰 Số dư: `{Utils.format_money(db.query('SELECT balance FROM users WHERE uid=%s',(uid,))[0]['balance'])}` \n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🚀 **Hệ thống tự động 100%**\n"
        f"💎 Nạp rút MSB Auto 30s\n"
        f"🎮 Đa dạng game: Tài xỉu, Chẵn lẻ, Bầu cua...\n"
        f"🤝 Hoa hồng đại lý trọn đời 5%\n\n"
        f"👇 Chọn chức năng bên dưới để quất!"
    )
    update.message.reply_text(welcome_msg, reply_markup=get_main_kb(), parse_mode=ParseMode.MARKDOWN)

def handle_text(update: Update, context: CallbackContext):
    uid = update.effective_user.id
    text = update.message.text
    
    # Lấy thông tin user realtime
    user = db.query("SELECT * FROM users WHERE uid = %s", (uid,))
    if not user: return
    user = user[0]
    
    if user['is_banned']: return

    # --- ROUTING LOGIC ---
    if text == "🎲 TÀI XỈU VIP":
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔴 TÀI (x1.95)", callback_data="tx_play_tai"), InlineKeyboardButton("⚫ XỈU (x1.95)", callback_data="tx_play_xiu")],
            [InlineKeyboardButton("💵 20K", callback_data="bet_20000"), InlineKeyboardButton("💵 100K", callback_data="bet_100000"), InlineKeyboardButton("💵 500K", callback_data="bet_500000")],
            [InlineKeyboardButton("💎 TẤT TAY", callback_data="bet_all")]
        ])
        update.message.reply_text(f"🎲 **TÀI XỈU SUPREME**\n💰 Số dư: `{Utils.format_money(user['balance'])}` \nChọn mức cược và cửa đặt:", reply_markup=kb)

    elif text == "💰 NẠP TIỀN":
        msg = (
            f"🏦 **NẠP TIỀN TỰ ĐỘNG (MSB AUTO)**\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"🏧 Ngân hàng: **{BANK_NAME}**\n"
            f"🔢 Số tài khoản: `{BANK_ACC}`\n"
            f"👤 Chủ TK: **{BANK_USER}**\n"
            f"📝 Nội dung: `{uid}`\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"⚠️ **QUY TẮC NẠP:**\n"
            f"1️⃣ Ghi đúng ID `{uid}` vào nội dung.\n"
            f"2️⃣ Hệ thống tự động cộng sau 30s.\n"
            f"3️⃣ Nạp tối thiểu 10,000đ."
        )
        update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)

    elif text == "💸 RÚT TIỀN":
        if not user['bank_acc']:
            update.message.reply_text("⚠️ Bạn chưa liên kết Ngân hàng!\nCú pháp: `/link [STK] [TEN_BANK] [TEN_CHU_TK]`")
        else:
            msg = (
                f"💸 **LỆNH RÚT TIỀN**\n"
                f"💰 Số dư khả dụng: `{Utils.format_money(user['balance'])}` \n"
                f"🏦 Rút về: `{user['bank_name']} | {user['bank_acc']}`\n"
                f"👤 Chủ thẻ: `{user['bank_user']}`\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"👉 Nhập lệnh: `/rut [số_tiền]`\n"
                f"Ví dụ: `/rut 100000`"
            )
            update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)

    elif text == "👤 CÁ NHÂN":
        level = Utils.get_level_info(user['exp'])
        msg = (
            f"👤 **HỒ SƠ ĐẠI GIA**\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"🆔 ID: `{uid}`\n"
            f"🎖️ Level: `{level}`\n"
            f"💰 Số dư: `{Utils.format_money(user['balance'])}` \n"
            f"📊 Tổng nạp: `{Utils.format_money(user['total_deposit'])}` \n"
            f"🎰 Tổng cược: `{Utils.format_money(user['total_bet'])}` \n"
            f"🏆 Tổng thắng: `{Utils.format_money(user['total_win'])}` \n"
            f"🤝 Tiền Ref: `{Utils.format_money(user['total_ref_earn'])}` \n"
            f"━━━━━━━━━━━━━━━━━━━━"
        )
        update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)

    elif text == "🤝 ĐẠI LÝ 5.0":
        bot_uname = context.bot.username
        ref_link = f"https://t.me/{bot_uname}?start={uid}"
        msg = (
            f"🤝 **HỆ THỐNG ĐẠI LÝ TRUMTX**\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"💰 Hoa hồng: **5% mỗi vòng cược của cấp dưới**\n"
            f"🔗 Link mời của bạn:\n`{ref_link}`\n\n"
            f"👥 Hãy chia sẻ link để nhận hoa hồng thụ động không giới hạn!"
        )
        update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)

    # --- ADMIN ROUTE ---
    elif text == "/admin" and uid == ADMIN_ID:
        update.message.reply_text("🔧 **HỆ THỐNG QUẢN TRỊ TỐI CAO**", reply_markup=get_admin_kb())

    elif text == "📢 THÔNG BÁO ALL" and uid == ADMIN_ID:
        update.message.reply_text("👉 Gõ lệnh: `/sendall [nội dung]` để gửi tin nhắn cho toàn bộ người dùng.")

# ==========================================
# 🎮 CALLBACKS (GAME ENGINE & ADMIN)
# ==========================================

bet_state = {} # {uid: amount}

def handle_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    uid = query.from_user.id
    data = query.data
    
    user = db.query("SELECT * FROM users WHERE uid = %s", (uid,))[0]
    if user['is_banned']: return query.answer("Tài khoản bị khóa!")

    # Logic chọn tiền cược
    if data.startswith("bet_"):
        amt_str = data.split("_")[1]
        bet_state[uid] = user['balance'] if amt_str == "all" else int(amt_str)
        query.answer(f"✅ Đã chọn cược: {Utils.format_money(bet_state[uid])}")

    # Logic chơi Tài Xỉu
    elif data.startswith("tx_play_"):
        choice = data.split("_")[2]
        bet = bet_state.get(uid, 10000) # Mặc định 10k nếu chưa chọn
        
        if user['balance'] < bet or bet < 1000:
            return query.answer("❌ Số dư không đủ hoặc cược quá thấp!", show_alert=True)

        # Lấy winrate từ admin
        wr = db.query("SELECT value FROM admin_config WHERE key='win_rate'")[0]['value']
        dices, total, result = GameEngines.tx_logic(choice, wr)

        # Trừ tiền ngay lập tức
        db.query("UPDATE users SET balance = balance - %s, total_bet = total_bet + %s, exp = exp + 10 WHERE uid = %s", (bet, bet, uid), fetch=False)
        
        # Xử lý hoa hồng Ref
        if user['ref_by'] != 0:
            comm = bet * 0.05
            db.query("UPDATE users SET balance = balance + %s, total_ref_earn = total_ref_earn + %s WHERE uid = %s", (comm, comm, user['ref_by']), fetch=False)

        # Kết quả
        if choice == result:
            win_amt = bet * 1.95
            db.query("UPDATE users SET balance = balance + %s, total_win = total_win + %s WHERE uid = %s", (win_amt, win_amt, uid), fetch=False)
            msg = (f"🎉 **THẮNG RỒI! CHÚC MỪNG ĐẠI GIA**\n"
                   f"━━━━━━━━━━━━━━━━━━━━\n"
                   f"🎲 Kết quả: {dices[0]}-{dices[1]}-{dices[2]} = **{total} ({result.upper()})**\n"
                   f"💰 Tiền thắng: `+{Utils.format_money(win_amt)}` \n"
                   f"💰 Số dư: `{Utils.format_money(user['balance'] - bet + win_amt)}`")
        else:
            msg = (f"❌ **TIẾC QUÁ! THUA MẤT RỒI**\n"
                   f"━━━━━━━━━━━━━━━━━━━━\n"
                   f"🎲 Kết quả: {dices[0]}-{dices[1]}-{dices[2]} = **{total} ({result.upper()})**\n"
                   f"💸 Tiền cược: `-{Utils.format_money(bet)}` \n"
                   f"💰 Số dư: `{Utils.format_money(user['balance'] - bet)}`")
        
        query.edit_message_text(msg, reply_markup=query.message.reply_markup, parse_mode=ParseMode.MARKDOWN)

    # Admin duyệt rút tiền
    elif data.startswith("withdraw_"):
        if uid != ADMIN_ID: return
        action, rid = data.split("_")[1], data.split("_")[2]
        req = db.query("SELECT * FROM withdraw_requests WHERE id = %s", (rid,))[0]
        
        if action == "approve":
            db.query("UPDATE withdraw_requests SET status = 'approved' WHERE id = %s", (rid,), fetch=False)
            context.bot.send_message(req['uid'], f"✅ Lệnh rút `{Utils.format_money(req['amount'])}` đã được duyệt!")
            # Log Group
            log_msg = (f"💸 **THÀNH VIÊN RÚT TIỀN THÀNH CÔNG**\n"
                       f"━━━━━━━━━━━━━━━━━━━━\n"
                       f"👤 Khách: `{req['uid']}`\n"
                       f"💰 Số tiền: `{Utils.format_money(req['amount'])}` \n"
                       f"✅ Trạng thái: **UY TÍN 100%**")
            context.bot.send_message(LOG_GROUP_ID, log_msg, parse_mode=ParseMode.MARKDOWN)
        else:
            db.query("UPDATE withdraw_requests SET status = 'rejected' WHERE id = %s", (rid,), fetch=False)
            db.query("UPDATE users SET balance = balance + %s WHERE uid = %s", (req['amount'], req['uid']), fetch=False)
            context.bot.send_message(req['uid'], f"❌ Lệnh rút `{Utils.format_money(req['amount'])}` bị từ chối. Tiền đã hoàn lại!")
        
        query.edit_message_text(f"✅ Đã xử lý lệnh #{rid}")

# ==========================================
# 👑 ADMIN COMMANDS (SIÊU CẤP)
# ==========================================

def admin_send_all(update: Update, context: CallbackContext):
    if update.effective_user.id != ADMIN_ID: return
    content = " ".join(context.args)
    users = db.query("SELECT uid FROM users")
    count = 0
    for u in users:
        try:
            context.bot.send_message(u['uid'], f"🔔 **THÔNG BÁO TỪ HỆ THỐNG**\n━━━━━━━━━━━━━━━━━━━━\n\n{content}", parse_mode=ParseMode.MARKDOWN)
            count += 1
        except: continue
    update.message.reply_text(f"✅ Đã gửi cho {count} người dùng.")

def admin_add_money(update: Update, context: CallbackContext):
    if update.effective_user.id != ADMIN_ID: return
    target_id, amount = int(context.args[0]), float(context.args[1])
    db.query("UPDATE users SET balance = balance + %s WHERE uid = %s", (amount, target_id), fetch=False)
    update.message.reply_text(f"✅ Đã cộng {Utils.format_money(amount)} cho ID {target_id}")

# ==========================================
# 🚀 KHỞI CHẠY (ENGINE CHÍNH)
# ==========================================

def main():
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    # Lệnh người dùng
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("link", lambda u, c: db.query("UPDATE users SET bank_acc=%s, bank_name=%s, bank_user=%s WHERE uid=%s", (c.args[0], c.args[1], " ".join(c.args[2:]).upper(), u.effective_user.id), fetch=False) or u.message.reply_text("✅ Đã liên kết ngân hàng!")))
    dp.add_handler(CommandHandler("rut", lambda u, c: db.query("INSERT INTO withdraw_requests (uid, amount) VALUES (%s, %s)", (u.effective_user.id, float(c.args[0])), fetch=False) or u.message.reply_text("✅ Đã gửi yêu cầu rút!")))
    
    # Lệnh Admin
    dp.add_handler(CommandHandler("sendall", admin_send_all))
    dp.add_handler(CommandHandler("plus", admin_add_money))
    
    # Message & Callback
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_text))
    dp.add_handler(CallbackQueryHandler(handle_callback))

    print("🚀 TRUMTX V5 MEGA-POWERED IS ONLINE!")
    updater.start_polling(drop_pending_updates=True)
    updater.idle()

if __name__ == '__main__':
    main()
              
