import random
import logging
import string
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackQueryHandler, CallbackContext
from telegram.parsemode import ParseMode

# ==========================================
# ⚙️ 1. CẤU HÌNH (THAY THÔNG TIN CỦA ÔNG VÀO ĐÂY)
# ==========================================
BOT_TOKEN = "8755060469:AAH1R02X_408_mNFPcOH8harJI25Z96UZL4"
ADMIN_ID = 7816353760  
GROUP_ID = -1003778771904 # ID Group để bot spam rút ảo

class BotState:
    def __init__(self):
        self.global_winrate = 50
        self.rut_ao_enabled = False
        self.giftcodes = {} # {code: {'amount': 10000, 'limit': 10, 'used': []}}

state = BotState()

# (Giả lập Database - Thay bằng MySQL của ông nếu cần)
class MockDatabase:
    def __init__(self):
        self.users = {} # {uid: {'balance': 0, 'name': ''}}

    def get_user(self, uid, name="Người chơi"):
        if uid not in self.users:
            self.users[uid] = {'balance': 100000, 'name': name} # Tặng 100k trải nghiệm
        return self.users[uid]

    def update_balance(self, uid, amount):
        user = self.get_user(uid)
        user['balance'] += amount
        return user['balance']

db = MockDatabase()

# ==========================================
# 🎲 2. CASINO ENGINE
# ==========================================
class Casino_Engine:
    def process_taixiu(self, uid, choice, amount, global_wr):
        user = db.get_user(uid)
        if user['balance'] < amount:
            return None, "❌ Số dư không đủ!"
        
        db.update_balance(uid, -amount)
        dices = [random.randint(1, 6) for _ in range(3)]
        
        # Can thiệp Winrate
        if random.randint(1, 100) > global_wr:
            if choice == "tai": dices = [1, 2, 2] # Ép thua
            else: dices = [5, 5, 6] # Ép thua
            
        total = sum(dices)
        result = "tai" if total >= 11 else "xiu"
        is_win = (choice == result)
        win_amt = int(amount * 1.95) if is_win else 0
        
        if is_win:
            db.update_balance(uid, win_amt)
            
        icons = {1: "1️⃣", 2: "2️⃣", 3: "3️⃣", 4: "4️⃣", 5: "5️⃣", 6: "6️⃣"}
        return {
            "dices": [icons[d] for d in dices],
            "total": total, "result": result, "is_win": is_win, "win_amount": win_amt,
            "new_balance": user['balance']
        }, None

casino = Casino_Engine()

# ==========================================
# 🤖 3. XỬ LÝ GIAO DIỆN
# ==========================================
def start(update: Update, context: CallbackContext):
    uid = update.effective_user.id
    db.get_user(uid, update.effective_user.first_name)
    
    msg = "💎 **CASINO HOÀNG GIA - XANH CHÍN 1:1** 💎\n\n💰 Nạp rút tự động, uy tín làm nên thương hiệu!"
    kb = [
        [KeyboardButton("🎲 TÀI XỈU VIP"), KeyboardButton("🎁 NHẬP GIFTCODE")],
        [KeyboardButton("👤 CÁ NHÂN"), KeyboardButton("💸 RÚT TIỀN")],
        [KeyboardButton("📞 HỖ TRỢ")]
    ]
    if uid == ADMIN_ID:
        kb.append([KeyboardButton("🛠 ADMIN PANEL")])
        
    update.message.reply_text(msg, reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True), parse_mode=ParseMode.MARKDOWN)

def handle_messages(update: Update, context: CallbackContext):
    text = update.message.text
    uid = update.effective_user.id
    user = db.get_user(uid)

    if text == "🎲 TÀI XỈU VIP":
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("10K", callback_data="bet_10000"), InlineKeyboardButton("50K", callback_data="bet_50000")],
            [InlineKeyboardButton("100K", callback_data="bet_100000"), InlineKeyboardButton("500K", callback_data="bet_500000")]
        ])
        update.message.reply_text(f"🎲 **TÀI XỈU VIP**\n💰 Số dư: `{user['balance']:,.0f}đ`\n👇 Chọn mức cược:", reply_markup=kb, parse_mode=ParseMode.MARKDOWN)

    elif text == "🎁 NHẬP GIFTCODE":
        update.message.reply_text("👉 Vui lòng gửi mã Giftcode của ông vào đây:")
        return context.user_data['waiting_giftcode'] = True

    elif text == "👤 CÁ NHÂN":
        update.message.reply_text(f"👤 **THÔNG TIN CÁ NHÂN**\n🆔 ID: `{uid}`\n💰 Số dư: `{user['balance']:,.0f}đ`", parse_mode=ParseMode.MARKDOWN)

    elif text == "🛠 ADMIN PANEL" and uid == ADMIN_ID:
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton(f"⚙️ Winrate: {state.global_winrate}%", callback_data="adm_set_wr")],
            [InlineKeyboardButton("✅ Bật Rút Ảo", callback_data="adm_ao_on"), InlineKeyboardButton("❌ Tắt Rút Ảo", callback_data="adm_ao_off")],
            [InlineKeyboardButton("🎁 Tạo Giftcode", callback_data="adm_gen_code")]
        ])
        update.message.reply_text("🛠 **QUẢN TRỊ VIÊN**", reply_markup=kb)

    # Xử lý nhập Giftcode
    if context.user_data.get('waiting_giftcode'):
        code = text.strip().upper()
        if code in state.giftcodes:
            gc = state.giftcodes[code]
            if uid in gc['used']:
                update.message.reply_text("❌ Mã này ông đã dùng rồi!")
            elif len(gc['used']) >= gc['limit']:
                update.message.reply_text("❌ Mã đã hết lượt sử dụng!")
            else:
                gc['used'].append(uid)
                db.update_balance(uid, gc['amount'])
                update.message.reply_text(f"✅ Thành công! +{gc['amount']:,.0f}đ vào tài khoản.")
        else:
            update.message.reply_text("❌ Mã không tồn tại!")
        context.user_data['waiting_giftcode'] = False

# ==========================================
# ⚡ 4. XỬ LÝ NÚT BẤM (CALLBACK)
# ==========================================
def button_handler(update: Update, context: CallbackContext):
    query = update.callback_query
    data = query.data
    uid = query.from_user.id
    query.answer()

    if data.startswith("bet_"):
        amt = int(data.split("_")[1])
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔴 TÀI", callback_data=f"p_tai_{amt}"), InlineKeyboardButton("⚫️ XỈU", callback_data=f"p_xiu_{amt}")]
        ])
        query.edit_message_text(f"💰 Cược: `{amt:,.0f}đ`\n👉 Chọn cửa đặt:", reply_markup=kb, parse_mode=ParseMode.MARKDOWN)

    elif data.startswith("p_"):
        _, choice, amt = data.split("_")
        res, err = casino.process_taixiu(uid, choice, int(amt), state.global_winrate)
        if err: return query.edit_message_text(err)
        
        txt = (f"🎲 Kết quả: {' '.join(res['dices'])} = {res['total']} ({res['result'].upper()})\n"
               f"👉 Cửa: {choice.upper()} | {'✅ THẮNG' if res['is_win'] else '💀 THUA'}\n"
               f"💰 Nhận: `{res['win_amount']:,.0f}đ` | Ví: `{res['new_balance']:,.0f}đ`")
        query.edit_message_text(txt, parse_mode=ParseMode.MARKDOWN)

    elif data == "adm_set_wr":
        state.global_winrate = 10 if state.global_winrate == 90 else state.global_winrate + 20
        query.edit_message_text(f"✅ Đã chỉnh Winrate hệ thống lên: {state.global_winrate}%", reply_markup=query.message.reply_markup)

    elif data == "adm_ao_on":
        state.rut_ao_enabled = True
        query.edit_message_text("✅ Đã bật spam rút tiền ảo!")
    elif data == "adm_ao_off":
        state.rut_ao_enabled = False
        query.edit_message_text("❌ Đã tắt spam rút tiền ảo!")

    elif data == "adm_gen_code":
        new_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
        state.giftcodes[new_code] = {'amount': 20000, 'limit': 50, 'used': []}
        query.message.reply_text(f"🎁 **GIFTCODE MỚI**\nCode: `{new_code}`\nSố tiền: 20k\nLượt nhập: 50", parse_mode=ParseMode.MARKDOWN)

# ==========================================
# 💸 5. SPAM RÚT TIỀN ẢO
# ==========================================
def cron_rut_ao(context: CallbackContext):
    if not state.rut_ao_enabled: return
    names = ["Hoàng ***", "Minh ***", "Văn ***", "Thị ***", "Công ***"]
    amts = ["200,000", "500,000", "1,000,000", "2,500,000"]
    banks = ["MBBank", "Vietcombank", "Techcombank", "Momo"]
    
    msg = (f"💸 **LỆNH RÚT THÀNH CÔNG** 💸\n"
           f"👤 Khách hàng: `{random.choice(names)}`\n"
           f"💰 Số tiền: `{random.choice(amts)}đ`\n"
           f"🏦 Ngân hàng: {random.choice(banks)}\n"
           f"⚡️ Trạng thái: **Hoàn tất (1s)**")
    try: context.bot.send_message(chat_id=GROUP_ID, text=msg, parse_mode=ParseMode.MARKDOWN)
    except: pass

# ==========================================
# 🚀 6. CHẠY BOT
# ==========================================
def main():
    updater = Updater(BOT_TOKEN, use_context=True)
    dp = updater.dispatcher
    
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_messages))
    dp.add_handler(CallbackQueryHandler(button_handler))
    
    # Spam rút ảo mỗi 2 phút
    updater.job_queue.run_repeating(cron_rut_ao, interval=120, first=10)

    print("🚀 BOT ĐÃ SẴN SÀNG KINH DOANH!")
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
  
