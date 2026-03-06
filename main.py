import os, re, requests, json, random, time, threading, logging, sys
from datetime import datetime, timedelta
from flask import Flask
from telegram import (InlineKeyboardButton, InlineKeyboardMarkup, Update, 
                      ParseMode, ReplyKeyboardMarkup, KeyboardButton, Bot, ChatMember)
from telegram.ext import (Updater, CommandHandler, CallbackQueryHandler, 
                          MessageHandler, Filters, CallbackContext, JobQueue)
from telegram.error import TelegramError
import psycopg2
from psycopg2.extras import RealDictCursor

# ==============================================================================
# 🌐 [SECTION 1] CONFIGURATION & GLOBAL SETTINGS
# ==============================================================================
TOKEN = "8755060469:AAH1R02X_408_mNFPcOH8harJI25Z96UZL4"
ADMIN_ID = 7816353760
GROUP_NOTI_ID = -1002445831627 
REQUIRED_CHANNEL_ID = -1003778771904 # ID Nhóm bắt buộc tham gia
CHANNEL_LINK = "https://t.me/TRUMTXCL" # Link nhóm để user click

DB_URL = "postgresql://postgres.naghdswctyyvzfdnforu:96886693002613@aws-1-ap-southeast-2.pooler.supabase.com:6543/postgres"

BANK_CONFIG = {
    "bank_name": "MSB",
    "account_number": "96886693002613",
    "account_holder": "NGUYEN THANH HOP",
    "min_withdraw": 50000,
    "min_deposit": 10000,
    "fee_withdraw": 0
}

# Hệ thống quản lý trạng thái Runtime
class SystemState:
    def __init__(self):
        self.marketing_active = False
        self.maintenance_mode = False
        self.global_winrate = 50
        self.total_users_online = 0
        self.last_fake_withdraw = None
        self.boot_time = datetime.now()

state = SystemState()

# Chống treo Render (Keep-alive)
app = Flask(__name__)
@app.route('/')
def health_check():
    return f"🚀 TRUMTX V5000 STATUS: OPERATIONAL\nUptime: {datetime.now() - state.boot_time}"

def run_web_server():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

# ==============================================================================
# 🗄️ [SECTION 2] ADVANCED DATABASE ARCHITECTURE
# ==============================================================================
class TrumTX_Database:
    def __init__(self):
        try:
            self.conn = psycopg2.connect(DB_URL, sslmode='require')
            self._create_tables()
            logging.info("✅ Database Connected & Migrated.")
        except Exception as e:
            logging.error(f"❌ Critical DB Error: {e}")
            sys.exit(1)

    def _create_tables(self):
        with self.conn.cursor() as cur:
            # Bảng Người dùng (Đầy đủ thuộc tính Casino)
            cur.execute('''CREATE TABLE IF NOT EXISTS users (
                uid BIGINT PRIMARY KEY,
                username TEXT,
                balance BIGINT DEFAULT 0,
                total_bet BIGINT DEFAULT 0,
                total_win BIGINT DEFAULT 0,
                total_deposit BIGINT DEFAULT 0,
                total_withdraw BIGINT DEFAULT 0,
                level INTEGER DEFAULT 1,
                exp INTEGER DEFAULT 0,
                bank_acc TEXT DEFAULT NULL,
                bank_name TEXT DEFAULT NULL,
                bank_user TEXT DEFAULT NULL,
                ref_by BIGINT DEFAULT 0,
                is_banned BOOLEAN DEFAULT FALSE,
                is_admin BOOLEAN DEFAULT FALSE,
                last_active TIMESTAMP DEFAULT NOW(),
                created_at TIMESTAMP DEFAULT NOW()
            )''')
            
            # Bảng Lịch sử đơn rút (Duyệt/Hủy)
            cur.execute('''CREATE TABLE IF NOT EXISTS withdraw_logs (
                id SERIAL PRIMARY KEY,
                uid BIGINT,
                amount BIGINT,
                bank_info TEXT,
                status TEXT DEFAULT 'PENDING',
                created_at TIMESTAMP DEFAULT NOW()
            )''')

            # Bảng Giftcode chuyên sâu
            cur.execute('''CREATE TABLE IF NOT EXISTS vouchers (
                code TEXT PRIMARY KEY,
                value BIGINT,
                max_uses INTEGER,
                current_uses INTEGER DEFAULT 0,
                min_level INTEGER DEFAULT 1,
                expired_at TIMESTAMP
            )''')
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
                logging.error(f"Query Error: {e}")
                return []

db = TrumTX_Database()

# ==============================================================================
# 🛡️ [SECTION 3] SECURITY & MIDDLEWARE (CHECK JOIN GROUP)
# ==============================================================================
class Middleware:
    @staticmethod
    def is_member(bot: Bot, user_id: int) -> bool:
        if user_id == ADMIN_ID: return True
        try:
            member = bot.get_chat_member(REQUIRED_CHANNEL_ID, user_id)
            return member.status in [ChatMember.MEMBER, ChatMember.ADMINISTRATOR, ChatMember.CREATOR]
        except TelegramError:
            return False

    @staticmethod
    def force_join_handler(update: Update, context: CallbackContext):
        user_id = update.effective_user.id
        if not Middleware.is_member(context.bot, user_id):
            msg = (f"⚠️ **YÊU CẦU THAM GIA NHÓM**\n\n"
                   f"Để sử dụng Bot, bạn phải tham gia nhóm thông báo của chúng tôi.\n"
                   f"Điều này giúp bạn cập nhật mã Giftcode và lịch sử nạp rút.\n\n"
                   f"🔗 Nhóm: {CHANNEL_LINK}")
            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ THAM GIA NGAY", url=CHANNEL_LINK)],
                [InlineKeyboardButton("🔄 TÔI ĐÃ THAM GIA", callback_data="check_joined")]
            ])
            update.message.reply_text(msg, reply_markup=kb, parse_mode=ParseMode.MARKDOWN)
            return False
        return True

# ==============================================================================
# 🎨 [SECTION 4] UI GENERATOR (MENU HỆ THỐNG)
# ==============================================================================
class UI:
    @staticmethod
    def main_menu(user_id):
        layout = [
            [KeyboardButton("🎲 TÀI XỈU VIP"), KeyboardButton("⚖️ CHẴN LẺ MSB")],
            [KeyboardButton("🦀 BẦU CUA"), KeyboardButton("🎡 VÒNG QUAY")],
            [KeyboardButton("🎯 NHIỆM VỤ"), KeyboardButton("🏆 TOP BXH")],
            [KeyboardButton("💰 NẠP TIỀN"), KeyboardButton("💸 RÚT TIỀN")],
            [KeyboardButton("👤 CÁ NHÂN"), KeyboardButton("🤝 ĐẠI LÝ")],
            [KeyboardButton("🏦 LIÊN KẾT BANK"), KeyboardButton("📞 HỖ TRỢ")]
        ]
        if user_id == ADMIN_ID:
            layout.append([KeyboardButton("🛠 ADMIN PANEL")])
        return ReplyKeyboardMarkup(layout, resize_keyboard=True)

    @staticmethod
    def admin_panel():
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("📈 BẬT RÚT ẢO", callback_data="adm_mkt_on"), 
             InlineKeyboardButton("📉 TẮT RÚT ẢO", callback_data="adm_mkt_off")],
            [InlineKeyboardButton("⚙️ WINRATE", callback_data="adm_wr"),
             InlineKeyboardButton("🎁 TẠO GIFTCODE", callback_data="adm_gen_code")],
            [InlineKeyboardButton("📊 THỐNG KÊ", callback_data="adm_stats"),
             InlineKeyboardButton("🚫 KHÓA USER", callback_data="adm_ban")])
        return InlineKeyboardMarkup(layout)

# =============================================================
class Casino_Engine:
    def __init__(self, db_instance):
        self.db = db_instance


        """Logic Tài Xỉu có can thiệp Winrate và lưu vết hệ thống"""
        # 1. Kiểm tra số dư & Trừ tiền trước
        user = self.db.query("SELECT balance FROM users WHERE uid = %s", (uid,))[0]
        if user['balance'] < amount:
            return None, "❌ Số dư không đủ!"

        self.db.query("UPDATE users SET balance = balance - %s, total_bet = total_bet + %s WHERE uid = %s", 
                      (amount, amount, uid), fetch=False)

        # 2. Quay xúc xắc (Dựa trên Winrate)
        dices = [random.randint(1, 6) for _ in range(3)]
        total = sum(dices)
        result = "tai" if total >= 11 else "xiu"

        # Can thiệp Winrate: Nếu random > Winrate thì ép thua
        if random.randint(1, 100) > global_wr:
            if choice == "tai" and result == "tai":
                dices = [random.randint(1, 3), random.randint(1, 3), random.randint(1, 4)]
            elif choice == "xiu" and result == "xiu":
                dices = [random.randint(4, 6), random.randint(4, 6), random.randint(3, 6)]
            total = sum(dices)
            result = "xiu" if total < 11 else "tai"

        # 3. Tính tiền thắng
        is_win = (choice == result)
        win_amount = int(amount * 1.95) if is_win else 0

        if is_win:
            self.db.query("UPDATE users SET balance = balance + %s, total_win = total_win + %s, exp = exp + %s WHERE uid = %s", 
                          (win_amount, win_amount, int(amount/1000), uid), fetch=False)
        
        return {
            "dices": dices,
            "total": total,
            "result": result,
            "is_win": is_win,
            "win_amount": win_amount,
            "dice_icons": [self.icons[d] for d in dices]
        }, None

    def process_baucua(self, uid, bets_dict):
        """bets_dict: {'bau': 10000, 'cua': 5000}"""
        total_bet = sum(bets_dict.values())
        user = self.db.query("SELECT balance FROM users WHERE uid = %s", (uid,))[0]
        
        if user['balance'] < total_bet:
            return None, "❌ Số dư không đủ cược!"

        self.db.query("UPDATE users SET balance = balance - %s, total_bet = total_bet + %s WHERE uid = %s", 
                      (total_bet, total_bet, uid), fetch=False)

        # Quay 3 linh vật
        items = ["bau", "cua", "tom", "ca", "ga", "nai"]
        results = [random.choice(items) for _ in range(3)]
        res_icons = [self.icons[r] for r in results]

        total_win = 0
        details = []
        for choice, amt in bets_dict.items():
            count = results.count(choice)
            if count > 0:
                win_val = amt * (count + 1)
                total_win += win_val
                details.append(f"✅ {self.icons[choice]} x{count}: +{win_val:,.0f}đ")
            else:
                details.append(f"❌ {self.icons[choice]}: -{amt:,.0f}đ")

        if total_win > 0:
            self.db.query("UPDATE users SET balance = balance + %s, total_win = total_win + %s WHERE uid = %s", 
                          (total_win, total_win, uid), fetch=False)

        return {
            "results": results,
            "res_icons": res_icons,
            "total_win": total_win,
            "details": details
        }, None

    def process_vongquay(self, uid):
        """Vòng quay may mắn - Phân phối tỉ lệ giải thưởng chuyên nghiệp"""
        cost = 20000
        user = self.db.query("SELECT balance FROM users WHERE uid = %s", (uid,))[0]
        if user['balance'] < cost:
            return None, "❌ Cần 20,000đ để quay!"

        self.db.query("UPDATE users SET balance = balance - %s WHERE uid = %s", (cost, uid), fetch=False)

        prizes = [
            (0, "Chúc bạn may mắn lần sau", 40),
            (10000, "Giải khuyến khích", 25),
            (30000, "Giải Ba", 15),
            (50000, "Giải Nhì", 10),
            (100000, "Giải Nhất", 7),
            (500000, "💥 SIÊU HŨ 💥", 3)
        ]
        
        pick = random.choices(prizes, weights=[p[2] for p in prizes])[0]
        win_amt = pick[0]

        if win_amt > 0:
            self.db.query("UPDATE users SET balance = balance + %s WHERE uid = %s", (win_amt, uid), fetch=False)
        
        return {"amount": win_amt, "name": pick[1]}, None

casino = Casino_Engine(db)

# ==============================================================================
# 📈 [SECTION 6] LEVEL & RANKING SYSTEM
# ==============================================================================
class Ranking_System:
    @staticmethod
    def get_top_balance():
        return db.query("SELECT username, balance FROM users ORDER BY balance DESC LIMIT 10")

    @staticmethod
    def get_top_bet():
        return db.query("SELECT username, total_bet FROM users ORDER BY total_bet DESC LIMIT 10")

    @staticmethod
    def check_level_up(uid):
        user = db.query("SELECT level, exp FROM users WHERE uid = %s", (uid,))[0]
        # Công thức: Level sau cần (Level hiện tại * 1000) EXP
        required = user['level'] * 1000
        if user['exp'] >= required:
            new_lvl = user['level'] + 1
            db.query("UPDATE users SET level = %s, exp = exp - %s WHERE uid = %s", (new_lvl, required, uid), fetch=False)
            return new_lvl
        return None

# ==============================================================================
# 🤝 [SECTION 7] REFERRAL & COMMISSION (ĐẠI LÝ)
# ==============================================================================
class Affiliate_System:
    @staticmethod
    def add_ref(uid, ref_id):
        if uid == ref_id: return False
        # Kiểm tra xem user đã có ref chưa
        user = db.query("SELECT ref_by FROM users WHERE uid = %s", (uid,))[0]
        if user['ref_by'] != 0: return False
        
        db.query("UPDATE users SET ref_by = %s WHERE uid = %s", (ref_id, uid), fetch=False)
        return True

    @staticmethod
    def pay_commission(uid, bet_amount):
        """Trả 0.5% tiền cược cho cấp trên"""
        user = db.query("SELECT ref_by FROM users WHERE uid = %s", (uid,))[0]
        if user['ref_by'] != 0:
            comm = int(bet_amount * 0.005)
            if comm > 0:
                db.query("UPDATE users SET balance = balance + %s, commission = commission + %s WHERE uid = %s", 
                         (comm, comm, user['ref_by']), fetch=False)
      # ==============================================================================
# 🤖 [SECTION 8] SIÊU ENGINE MARKETING (RÚT TIỀN ẢO TỐI THƯỢNG)
# ==============================================================================
class Marketing_Core:
    def __init__(self, bot: Bot):
        self.bot = bot
        self.fake_names = ["Tuấn", "Hoàng", "Linh", "Hùng", "Lan", "Dương", "Cường", "Bảo", "Trâm", "Nam", "Việt", "Phong", "Thảo"]
        self.fake_banks = ["MBBANK", "VCB", "ACB", "MSB", "TCB", "BIDV", "VTB"]

    def generate_fake_withdraw(self):
        """Tạo dữ liệu rút tiền ảo không vết nứt"""
        if not state.marketing_active:
            return

        # Random ID người dùng giả (7 số cuối)
        fake_uid = random.randint(1000000, 9999999)
        # Số tiền tròn: 200k, 500k, 1tr, 2tr, 5tr, 10tr... (Tuyệt đối không số lẻ)
        amounts = [100000, 200000, 500000, 1000000, 2000000, 5000000, 10000000]
        amt = random.choice(amounts)
        
        # Giả lập số dư còn lại (phải lớn hơn số tiền rút để kích thích khách nạp)
        fake_balance = random.randint(50000, 25000000)
        
        # Mã đơn giả ngẫu nhiên
        fake_order_id = random.randint(10000, 99999)
        
        msg = (f"🚀 **SAO KÊ RÚT TIỀN THÀNH CÔNG**\n"
               f"━━━━━━━━━━━━━━━━━━\n"
               f"✅ **Trạng thái:** Hoàn tất đơn `#{fake_order_id}`\n"
               f"👤 **Khách hàng:** `****{str(fake_uid)[-4:]}`\n"
               f"💰 **Số tiền rút:** `{amt:,.0f} VNĐ`\n"
               f"💳 **Số dư còn lại:** `{fake_balance:,.0f} VNĐ`\n"
               f"🏦 **Ngân hàng:** {random.choice(self.fake_banks)} Auto\n"
               f"⏰ **Thời gian:** {datetime.now().strftime('%H:%M:%S')}\n"
               f"━━━━━━━━━━━━━━━━━━\n"
               f"💎 *Uy tín tạo nên thương hiệu TRUMTX!*")

        try:
            self.bot.send_message(GROUP_NOTI_ID, msg, parse_mode=ParseMode.MARKDOWN)
        except Exception as e:
            logging.error(f"MKT Error: {e}")

# ==============================================================================
# 🛠️ [SECTION 9] ADMIN COMMAND CENTER (Duyệt đơn & Điều khiển)
# ==============================================================================
class Admin_Controller:
    @staticmethod
    def approve_withdraw(update: Update, context: CallbackContext, order_id):
        """Duyệt rút tiền thật - Bắn thông báo Group chuẩn 100%"""
        order = db.query("SELECT * FROM withdraw_logs WHERE id = %s", (order_id,))
        if not order or order[0]['status'] != 'PENDING':
            return False
            
        order = order[0]
        db.query("UPDATE withdraw_logs SET status = 'SUCCESS' WHERE id = %s", (order_id,), fetch=False)
        
        # Lấy số dư thực tế hiện tại của User để hiện vào thông báo Group
        user_balance = db.query("SELECT balance FROM users WHERE uid = %s", (order['uid'],))[0]['balance']
        
        msg_group = (f"🚀 **SAO KÊ RÚT TIỀN THÀNH CÔNG**\n"
                     f"━━━━━━━━━━━━━━━━━━\n"
                     f"✅ **Trạng thái:** Hoàn tất đơn `#{order_id}`\n"
                     f"👤 **Khách hàng:** `****{str(order['uid'])[-4:]}`\n"
                     f"💰 **Số tiền rút:** `{order['amount']:,.0f} VNĐ`\n"
                     f"💳 **Số dư còn lại:** `{user_balance:,.0f} VNĐ`\n"
                     f"⏰ **Thời gian:** {datetime.now().strftime('%H:%M:%S')}\n"
                     f"━━━━━━━━━━━━━━━━━━")
        
        try:
            context.bot.send_message(GROUP_NOTI_ID, msg_group, parse_mode=ParseMode.MARKDOWN)
            context.bot.send_message(order['uid'], f"✅ **RÚT TIỀN THÀNH CÔNG!**\nĐơn hàng `#{order_id}` trị giá `{order['amount']:,.0f}đ` đã được thanh toán.")
        except: pass
        return True

    @staticmethod
    def handle_admin_callback(update: Update, context: CallbackContext):
        query = update.callback_query
        data = query.data
        uid = query.from_user.id
        
        if uid != ADMIN_ID: return

        if data == "adm_mkt_on":
            state.marketing_active = True
            # Tạo Job ngẫu nhiên từ 3 đến 12 phút bắn 1 lần
            interval = random.randint(180, 720)
            context.job_queue.run_repeating(
                lambda ctx: Marketing_Core(ctx.bot).generate_fake_withdraw(),
                interval=interval, first=10, name="mkt_job"
            )
            query.edit_message_text("✅ Đã BẬT hệ thống Rút ảo ngẫu nhiên!", reply_markup=UI.admin_panel())
            
        elif data == "adm_mkt_off":
            state.marketing_active = False
            for job in context.job_queue.get_jobs_by_name("mkt_job"):
                job.schedule_removal()
            query.edit_message_text("❌ Đã TẮT hệ thống Rút ảo!", reply_markup=UI.admin_panel())

        elif data.startswith("approve_real_"):
            oid = int(data.split("_")[-1])
            if Admin_Controller.approve_withdraw(update, context, oid):
                query.edit_message_text(f"✅ Đã duyệt đơn #{oid} và bắn Group thành công!")
            else:
                query.answer("❌ Đơn đã xử lý hoặc không tồn tại!")

# ==============================================================================
# 📩 [SECTION 10] MESSAGE & CALLBACK DISPATCHER
# ==============================================================================
def handle_all_messages(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    text = update.message.text
    
    # [MIDDLEWARE] Ép Join Group - Không Join không cho dùng
    if not Middleware.force_join_handler(update, context):
        return

    # Khởi tạo user nếu chưa có
    user_data = db.query("SELECT * FROM users WHERE uid = %s", (user_id,))
    if not user_data:
        db.query("INSERT INTO users (uid, username) VALUES (%s, %s)", (user_id, update.effective_user.first_name), fetch=False)
        user = db.query("SELECT * FROM users WHERE uid = %s", (user_id,))[0]
    else:
        user = user_data[0]

    # LOGIC MENU CHÍNH
    if text == "🎲 TÀI XỈU VIP":
        msg = (f"🎲 **TÀI XỈU TRUMTX VIP**\n"
               f"💰 Số dư: `{user['balance']:,.0f}đ`\n\n"
               f"Vui lòng chọn mức cược và đặt cửa bên dưới👇")
        kb_bet = InlineKeyboardMarkup([
            [InlineKeyboardButton("💵 50K", callback_data="set_1_50000"), InlineKeyboardButton("💵 100K", callback_data="set_1_100000")],
            [InlineKeyboardButton("🔴 TÀI (x1.95)", callback_data="play_tx_tai"), InlineKeyboardButton("⚫ XỈU (x1.95)", callback_data="play_tx_xiu")]
        ])
        update.message.reply_text(msg, reply_markup=kb_bet, parse_mode=ParseMode.MARKDOWN)

    elif text == "💸 RÚT TIỀN":
        if not user['bank_acc']:
            return update.message.reply_text("❌ Bạn chưa liên kết ngân hàng! Hãy dùng nút **LIÊN KẾT BANK**.")
        update.message.reply_text(f"💸 Số dư khả dụng: `{user['balance']:,.0f} VNĐ`\n\n👉 Nhập lệnh rút: `/rut [số_tiền]`\n*(VD: /rut 100000)*")

    elif text == "🛠 ADMIN PANEL" and user_id == ADMIN_ID:
        update.message.reply_text("👑 **HỆ THỐNG QUẢN TRỊ TRUMTX V5000**", reply_markup=UI.admin_panel())

    elif text == "👤 CÁ NHÂN":
        bank_status = "✅ Đã liên kết" if user['bank_acc'] else "❌ Chưa liên kết"
        msg = (f"👤 **THÔNG TIN TÀI KHOẢN**\n"
               f"🆔 ID: `{user_id}`\n"
               f"💰 Số dư: `{user['balance']:,.0f}đ`\n"
               f"📊 Tổng cược: `{user['total_bet']:,.0f}đ`\n"
               f"🏦 Ngân hàng: {bank_status}\n"
               f"🤝 Đại lý: `{user['ref_by']}`")
        update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)

    elif text == "🏦 LIÊN KẾT BANK":
        update.message.reply_text("📝 **LIÊN KẾT NGÂN HÀNG**\n\nNhập theo cú pháp: `/link [STK] [TÊN_BANK] [TÊN_CHỦ_TK]`\n\nVD: `/link 123456 MSB NGUYEN VAN A`")

# ==============================================================================
# 🔄 [SECTION 11] CALLBACK HANDLER (XỬ LÝ NÚT BẤM GAME)
# ==============================================================================
user_temp_amt = {} # Lưu tạm tiền cược

def handle_callback_query(update: Update, context: CallbackContext):
    query = update.callback_query
    uid = query.from_user.id
    data = query.data
    
    # Phân luồng Admin
    if data.startswith("adm_") or data.startswith("approve_"):
        Admin_Controller.handle_admin_callback(update, context)
        return

    # Check Join lại nếu User bấm nút "TÔI ĐÃ THAM GIA"
    if data == "check_joined":
        if Middleware.is_member(context.bot, uid):
            query.edit_message_text("✅ Xác thực thành công! Chào mừng bạn quay lại.")
            context.bot.send_message(uid, "🔥 Bạn đã mở khóa toàn bộ tính năng!", reply_markup=UI.main_menu(uid))
        else:
            query.answer("❌ Bạn vẫn chưa tham gia nhóm!", show_alert=True)
        return

    # Logic Cược Game
    if data.startswith("set_1_"):
        user_temp_amt[uid] = int(data.split("_")[-1])
        query.answer(f"✅ Đã chọn cược: {user_temp_amt[uid]:,.0f}đ")
        
    elif data.startswith("play_tx_"):
        # Logic cược tài xỉu (Sử dụng Engine ở P2)
        choice = data.split("_")[-1]
        amt = user_temp_amt.get(uid, 0)
        if amt <= 0: return query.answer("⚠️ Chọn tiền cược trước!", show_alert=True)
        
        result, err = casino.process_taixiu(uid, choice, amt, state.global_winrate)
        if err: return query.answer(err, show_alert=True)
        
        # Hiệu ứng lắc
        query.edit_message_text("🎲 Đang lắc xúc xắc...")
        time.sleep(1)
        
        res_str = f"{' '.join(result['dice_icons'])} = `{result['total']}` ({result['result'].upper()})"
        if result['is_win']:
            msg = f"🎉 **THẮNG RỒI!**\n\n{res_str}\n💰 Nhận được: `+{result['win_amount']:,.0f} VNĐ`"
        else:
            msg = f"❌ **THUA RỒI!**\n\n{res_str}\n💸 Mất: `-{amt:,.0f} VNĐ`"
            
        query.edit_message_text(msg, parse_mode=ParseMode.MARKDOWN, reply_markup=UI.main_menu(uid))
      # ==============================================================================
# 🎁 [SECTION 12] GIFTCODE & VOUCHER SYSTEM (HỆ THỐNG MÃ TẶNG THƯỞNG)
# ==============================================================================
class Giftcode_Manager:
    @staticmethod
    def create_code(code, value, max_uses, min_lvl=1):
        """Admin tạo mã Code thưởng"""
        db.query("INSERT INTO vouchers (code, value, max_uses, min_level) VALUES (%s, %s, %s, %s)", 
                 (code.upper(), value, max_uses, min_lvl), fetch=False)
        return True

    @staticmethod
    def use_code(uid, code_str):
        code_str = code_str.upper()
        # 1. Kiểm tra mã tồn tại
        res = db.query("SELECT * FROM vouchers WHERE code = %s", (code_str,))
        if not res: return "❌ Mã Giftcode không tồn tại!"
        
        voucher = res[0]
        user = db.query("SELECT level, balance FROM users WHERE uid = %s", (uid,))[0]

        # 2. Kiểm tra điều kiện
        if voucher['current_uses'] >= voucher['max_uses']:
            return "❌ Mã này đã hết lượt sử dụng!"
        if user['level'] < voucher['min_level']:
            return f"❌ Yêu cầu Level {voucher['min_level']} để dùng mã này!"
            
        # 3. Thực hiện cộng tiền & Tăng lượt dùng
        db.query("UPDATE users SET balance = balance + %s WHERE uid = %s", (voucher['value'], uid), fetch=False)
        db.query("UPDATE vouchers SET current_uses = current_uses + 1 WHERE code = %s", (code_str,), fetch=False)
        
        return f"✅ Nhập mã thành công! Bạn nhận được `+{voucher['value']:,.0f} VNĐ`"

# ==============================================================================
# 🦀 [SECTION 13] BẦU CUA ENGINE - XỬ LÝ ĐẶT CƯỢC PHỨC TẠP
# ==============================================================================
user_baucua_session = {} # Lưu trạng thái đặt cửa tạm thời của User

def handle_baucua_logic(update: Update, context: CallbackContext):
    query = update.callback_query
    uid = query.from_user.id
    data = query.data

    if data == "menu_baucua":
        user_baucua_session[uid] = {"bau": 0, "cua": 0, "tom": 0, "ca": 0, "ga": 0, "nai": 0}
        return UI.show_baucua_table(query, uid)

    if data.startswith("bet_bc_"):
        item = data.split("_")[-1]
        # Mỗi lần bấm cộng 10k vào cửa đó
        user_baucua_session[uid][item] += 10000
        UI.show_baucua_table(query, uid)

    if data == "confirm_baucua":
        bets = {k: v for k, v in user_baucua_session[uid].items() if v > 0}
        if not bets: return query.answer("⚠️ Bạn chưa đặt cửa nào!", show_alert=True)
        
        result, err = casino.process_baucua(uid, bets)
        if err: return query.answer(err, show_alert=True)
        
        # Trình diễn kết quả
        res_text = " ".join(result['res_icons'])
        detail_text = "\n".join(result['details'])
        msg = (f"🎰 **KẾT QUẢ BẦU CUA**\n"
               f"━━━━━━━━━━━━━━\n"
               f"🎲 Kết quả: {res_text}\n\n"
               f"{detail_text}\n"
               f"━━━━━━━━━━━━━━\n"
               f"💰 Tổng nhận: `+{result['total_win']:,.0f}đ`")
        
        query.edit_message_text(msg, parse_mode=ParseMode.MARKDOWN, reply_markup=UI.main_menu(uid))
        del user_baucua_session[uid]

# ==============================================================================
# 🎯 [SECTION 14] DAILY MISSIONS (NHIỆM VỤ HÀNG NGÀY)
# ==============================================================================
class Mission_System:
    @staticmethod
    def get_missions(uid):
        user = db.query("SELECT total_bet, total_win FROM users WHERE uid = %s", (uid,))[0]
        # Giả lập danh sách nhiệm vụ dựa trên dữ liệu cược
        missions = [
            {"name": "Cược tổng 500k", "goal": 500000, "current": user['total_bet'], "reward": 10000},
            {"name": "Thắng tổng 200k", "goal": 200000, "current": user['total_win'], "reward": 5000}
        ]
        return missions

# ==============================================================================
# ⚡ [SECTION 15] COMMAND HANDLERS (XỬ LÝ LỆNH CHAT)
# ==============================================================================
def cmd_start(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    # Check ref nếu có tham số start
    if context.args:
        try:
            ref_id = int(context.args[0])
            Affiliate_System.add_ref(user_id, ref_id)
        except: pass

    update.message.reply_text(
        f"🔥 **CHÀO MỪNG ĐẾN VỚI TRUMTX V5000**\n\n"
        f"Hệ thống Casino Telegram uy tín số 1 Việt Nam.\n"
        f"Nạp rút tự động - Tỉ lệ xanh chín!\n\n"
        f"👇 Chọn chức năng bên dưới để bắt đầu:",
        reply_markup=UI.main_menu(user_id),
        parse_mode=ParseMode.MARKDOWN
    )

def cmd_rut_tien(update: Update, context: CallbackContext):
    uid = update.effective_user.id
    if not context.args: return
    try:
        amount = int(context.args[0])
        if amount < BANK_CONFIG['min_withdraw']:
            return update.message.reply_text(f"❌ Tối thiểu rút {BANK_CONFIG['min_withdraw']:,.0f}đ")
        
        user = db.query("SELECT balance, bank_acc FROM users WHERE uid = %s", (uid,))[0]
        if user['balance'] < amount:
            return update.message.reply_text("❌ Số dư không đủ!")
            
        # Tạo đơn rút
        db.query("UPDATE users SET balance = balance - %s WHERE uid = %s", (amount, uid), fetch=False)
        db.query("INSERT INTO withdraw_logs (uid, amount, bank_info) VALUES (%s, %s, %s)", 
                 (uid, amount, user['bank_acc']), fetch=False)
        
        # Lấy ID đơn vừa tạo
        order_id = db.query("SELECT id FROM withdraw_logs WHERE uid = %s ORDER BY id DESC LIMIT 1", (uid,))[0]['id']
        
        # Bắn thông báo cho Admin duyệt
        msg_adm = (f"🔔 **CÓ ĐƠN RÚT MỚI**\n"
                   f"👤 User: `{uid}`\n"
                   f"💰 Số tiền: `{amount:,.0f}đ`\n"
                   f"🏦 STK: `{user['bank_acc']}`")
        kb_adm = InlineKeyboardMarkup([[InlineKeyboardButton("✅ DUYỆT ĐƠN", callback_data=f"approve_real_{order_id}")]])
        context.bot.send_message(ADMIN_ID, msg_adm, reply_markup=kb_adm)
        
        update.message.reply_text(f"✅ Đã gửi yêu cầu rút `{amount:,.0f}đ`. Vui lòng chờ Admin duyệt!")
    except:
        update.message.reply_text("⚠️ Cú pháp: `/rut [số_tiền]`")

# ==============================================================================
# 🚀 [SECTION 16] MAIN INITIALIZATION (KHỞI CHẠY)
# ==============================================================================
def main():
    # 1. Khởi tạo Web Server giữ Bot sống 24/7
    threading.Thread(target=run_web_server, daemon=True).start()

    # 2. Thiết lập Telegram Bot
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    # Đăng ký lệnh chat
    dp.add_handler(CommandHandler("start", cmd_start))
    dp.add_handler(CommandHandler("rut", cmd_rut_tien))
    dp.add_handler(CommandHandler("code", lambda u, c: u.message.reply_text(Giftcode_Manager.use_code(u.effective_user.id, c.args[0])) if c.args else None))

    # Xử lý tin nhắn văn bản (Menu)
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_all_messages))
    
    # Xử lý nút bấm Inline (Game & Admin)
    dp.add_handler(CallbackQueryHandler(handle_callback_query))

    # 3. Bắt đầu quét tin nhắn
    print("------------------------------------------")
    print("💎 TRUMTX V5000 IS NOW ONLINE")
    print(f"👑 ADMIN: {ADMIN_ID}")
    print("------------------------------------------")
    
    updater.start_polling(drop_pending_updates=True)
    updater.idle()
# ==============================================================================
# 🏦 [SECTION 17] AUTO DEPOSIT SYSTEM (HỆ THỐNG NẠP TỰ ĐỘNG V5000)
# ==============================================================================
class Deposit_Engine:
    def __init__(self, bot: Bot):
        self.bot = bot
        self.min_deposit = BANK_CONFIG['min_deposit']

    @staticmethod
    def generate_qr(uid, amount=0):
        """Tạo link QR VietQR theo chuẩn Napas để User quét là hiện nội dung ID"""
        bank_id = BANK_CONFIG['bank_name']
        account = BANK_CONFIG['account_number']
        template = "compact" # Hoặc "qr_only"
        
        # Link VietQR: https://img.vietqr.io/image/<BANK_ID>-<ACCOUNT_NO>-<TEMPLATE>.png?amount=<AMOUNT>&addInfo=<CONTENT>
        qr_url = f"https://img.vietqr.io/image/{bank_id}-{account}-{template}.png?amount={amount}&addInfo={uid}"
        return qr_url

    def process_deposit_request(self, update: Update, context: CallbackContext):
        uid = update.effective_user.id
        msg = (f"💳 **NẠP TIỀN TỰ ĐỘNG 24/7**\n"
               f"━━━━━━━━━━━━━━━━━━\n"
               f"🏦 Ngân hàng: **{BANK_CONFIG['bank_name']}**\n"
               f"🔢 Số tài khoản: `{BANK_CONFIG['account_number']}`\n"
               f"👤 Chủ tài khoản: **{BANK_CONFIG['account_holder']}**\n"
               f"📝 Nội dung chuyển khoản: `{uid}`\n"
               f"━━━━━━━━━━━━━━━━━━\n"
               f"⚠️ **LƯU Ý:**\n"
               f"1. Chuyển đúng nội dung là **ID của bạn** ({uid}).\n"
               f"2. Hệ thống tự động cộng tiền sau 30s - 1 phút.\n"
               f"3. Nạp tối thiểu: `{self.min_deposit:,.0f}đ`.")
        
        qr_code = self.generate_qr(uid)
        
        # Gửi ảnh QR kèm thông tin
        try:
            context.bot.send_photo(
                chat_id=uid,
                photo=qr_code,
                caption=msg,
                parse_mode=ParseMode.MARKDOWN
            )
        except:
            update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)

    @staticmethod
    def auto_check_transaction(context: CallbackContext):
        """
        Đây là hàm chạy ngầm (Cronjob) để check API Ngân hàng.
        Vì mỗi ngân hàng có API khác nhau (MB, TCB, VCB...), 
        ở đây tôi viết Logic xử lý sau khi nhận được Webhook hoặc Data API.
        """
        # Giả lập: Lấy danh sách giao dịch mới từ API Ngân hàng (Payload giả định)
        # Trong thực tế, ông cần tích hợp API của bên thứ 3 như Casso.vn hoặc Web2M
        fake_api_data = [] # Giả sử có list giao dịch mới từ API
        
        for tx in fake_api_data:
            content = tx['description'] # Nội dung chuyển khoản
            amount = tx['amount']
            
            # Kiểm tra xem nội dung có phải là UID của user không
            try:
                user_id = int(re.search(r'\d+', content).group())
                user = db.query("SELECT * FROM users WHERE uid = %s", (user_id,))
                
                if user and amount >= BANK_CONFIG['min_deposit']:
                    # Cộng tiền cho User
                    db.query("UPDATE users SET balance = balance + %s, total_deposit = total_deposit + %s WHERE uid = %s", 
                             (amount, amount, user_id), fetch=False)
                    
                    # Báo tin nhắn cho User
                    context.bot.send_message(user_id, f"✅ **NẠP TIỀN THÀNH CÔNG!**\n💰 Đã cộng: `+{amount:,.0f}đ` vào tài khoản.")
                    
                    # Bắn thông báo Group cho uy tín
                    msg_noti = (f"💳 **THÔNG BÁO NẠP TIỀN**\n"
                                f"👤 Khách: `****{str(user_id)[-4:]}`\n"
                                f"💰 Số tiền: `+{amount:,.0f} VNĐ`\n"
                                f"✅ Trạng thái: **Thành công**")
                    context.bot.send_message(GROUP_NOTI_ID, msg_noti)
            except:
                continue

# ==============================================================================
# 🛠️ [SECTION 18] ADMIN PLUS MONEY (CỘNG TIỀN THỦ CÔNG)
# ==============================================================================
def admin_plus_money(update: Update, context: CallbackContext):
    """Lệnh cho Admin cộng tiền nhanh cho khách: /plus [ID] [SỐ_TIỀN]"""
    if update.effective_user.id != ADMIN_ID: return
    
    try:
        target_id = int(context.args[0])
        amount = int(context.args[1])
        
        db.query("UPDATE users SET balance = balance + %s WHERE uid = %s", (amount, target_id), fetch=False)
        
        update.message.reply_text(f"✅ Đã cộng `+{amount:,.0f}đ` cho User `{target_id}`.")
        context.bot.send_message(target_id, f"🎊 Bạn được Admin cộng `+{amount:,.0f}đ` vào tài khoản!")
    except:
        update.message.reply_text("⚠️ Cú pháp: `/plus [ID] [SỐ_TIỀN]`")

# ==============================================================================
# 🚀 CẬP NHẬT TRONG HÀM handle_all_messages (PHẦN 3)
# ==============================================================================
# Tìm đoạn 'elif text == "💰 NẠP TIỀN":' và thay thế bằng:
#
# elif text == "💰 NẠP TIỀN":
#     dep_engine = Deposit_Engine(context.bot)
#     dep_engine.process_deposit_request(update, context)
# ==============================================================================
# 🐲 [SECTION 19] GLOBAL JACKPOT SYSTEM (HỆ THỐNG NỔ HŨ TOÀN SÀN)
# ==============================================================================
class Jackpot_System:
    @staticmethod
    def get_jackpot():
        # Lấy tổng hũ từ file hoặc DB (Giả lập hũ đang có 50tr)
        res = db.query("SELECT SUM(total_bet) * 0.01 as hu_hien_tai FROM users")
        return int(res[0]['hu_hien_tai']) if res[0]['hu_hien_tai'] else 10000000

    @staticmethod
    def check_jackpot(uid, amount, context: CallbackContext):
        """Tỉ lệ nổ hũ 0.1% khi cược trên 50k"""
        if amount < 50000: return False
        
        chance = random.randint(1, 1000)
        if chance == 888: # Con số may mắn nổ hũ
            hu_tien = Jackpot_System.get_jackpot()
            db.query("UPDATE users SET balance = balance + %s WHERE uid = %s", (hu_tien, uid), fetch=False)
            
            # Thông báo chấn động Group
            msg = (f"🎊 🎉 **CHÚC MỪNG - NỔ HŨ SIÊU CẤP** 🎉 🎊\n"
                   f"━━━━━━━━━━━━━━━━━━━━\n"
                   f"👤 Người chơi: `****{str(uid)[-4:]}`\n"
                   f"💰 Số tiền nổ hũ: `{hu_tien:,.0f} VNĐ`\n"
                   f"🎮 Trò chơi: **Tài Xỉu VIP**\n"
                   f"━━━━━━━━━━━━━━━━━━━━\n"
                   f"🔥 Đẳng cấp đại gia là đây! Ai sẽ là người tiếp theo?")
            context.bot.send_message(GROUP_NOTI_ID, msg, parse_mode=ParseMode.MARKDOWN)
            context.bot.send_message(uid, f"🎁 **BẠN ĐÃ NỔ HŨ!**\nSố tiền `{hu_tien:,.0f}đ` đã được cộng vào tài khoản!")
            return True
        return False

# ==============================================================================
# 📅 [SECTION 20] DAILY ATTENDANCE (ĐIỂM DANH NHẬN QUÀ)
# ==============================================================================
user_last_checkin = {} # Lưu tạm thời gian điểm danh

def handle_attendance(update: Update, context: CallbackContext):
    uid = update.effective_user.id
    now = datetime.now()
    
    if uid in user_last_checkin:
        last_time = user_last_checkin[uid]
        if now - last_time < timedelta(days=1):
            return update.message.reply_text("❌ Hôm nay bạn đã điểm danh rồi! Hẹn gặp lại vào ngày mai.")
    
    reward = random.randint(1000, 5000)
    db.query("UPDATE users SET balance = balance + %s WHERE uid = %s", (reward, uid), fetch=False)
    user_last_checkin[uid] = now
    
    update.message.reply_text(f"✅ Điểm danh thành công!\n🎁 Bạn nhận được: `+{reward:,.0f}đ` tiền trải nghiệm.")

# ==============================================================================
# 🛡️ [SECTION 21] ANTI-SPAM & SYSTEM SECURITY
# ==============================================================================
user_spam_count = {}

def anti_spam_middleware(update: Update, context: CallbackContext):
    uid = update.effective_user.id
    now = time.time()
    
    if uid not in user_spam_count:
        user_spam_count[uid] = [now]
        return True
    
    # Nếu gửi quá 3 tin nhắn trong 2 giây -> Chặn
    user_spam_count[uid] = [t for t in user_spam_count[uid] if now - t < 2]
    user_spam_count[uid].append(now)
    
    if len(user_spam_count[uid]) > 3:
        update.message.reply_text("⚠️ **CẢNH BÁO:** Bạn đang thao tác quá nhanh! Vui lòng đợi 5 giây.")
        return False
    return True

# ==============================================================================
# 📊 [SECTION 22] ADMIN DASHBOARD (THỐNG KÊ CHI TIẾT)
# ==============================================================================
def get_admin_stats():
    total_u = db.query("SELECT COUNT(*) as cnt FROM users")[0]['cnt']
    total_bal = db.query("SELECT SUM(balance) as sm FROM users")[0]['sm']
    total_bet = db.query("SELECT SUM(total_bet) as sm FROM users")[0]['sm']
    
    msg = (f"📊 **THỐNG KÊ TOÀN SÀN**\n"
           f"━━━━━━━━━━━━━━\n"
           f"👥 Tổng User: `{total_u}`\n"
           f"💰 Tổng dư khách: `{total_bal:,.0f}đ`\n"
           f"🎲 Tổng cược: `{total_bet:,.0f}đ`\n"
           f"📈 Winrate: `{state.global_winrate}%`\n"
           f"🤖 Marketing: `{'BẬT' if state.marketing_active else 'TẮT'}`\n"
           f"━━━━━━━━━━━━━━")
    return msg

# ==============================================================================
# ⚙️ CẬP NHẬT TRONG MESSAGE HANDLER
# ==============================================================================
# Thêm vào trong handle_all_messages:
#
# elif text == "🎯 NHIỆM VỤ":
#      handle_attendance(update, context)
#
# elif text == "🏆 TOP BXH":
#      top = Ranking_System.get_top_balance()
#      msg = "🏆 **BẢNG XẾP HẠNG ĐẠI GIA**\n\n"
#      for i, u in enumerate(top):
#          msg += f"{i+1}. {u['username']} - `{u['balance']:,.0f}đ`\n"
#      update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)

if __name__ == "__main__":
    main()
              
