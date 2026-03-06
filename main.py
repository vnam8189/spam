import random
import string
import logging
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackQueryHandler, CallbackContext
from telegram.parsemode import ParseMode

# ==========================================
# ⚙️ 1. CẤU HÌNH (THAY ĐÚNG ID MỚI HIỆN ADMIN)
# ==========================================
BOT_TOKEN = "8755060469:AAH1R02X_408_mNFPcOH8harJI25Z96UZL4"
ADMIN_ID = 7816353760  # <--- THAY ID TELEGRAM CỦA ÔNG VÀO ĐÂY
GROUP_ID = -1003778771904 # ID Nhóm để bot spam rút ảo

class BotState:
    def __init__(self):
        self.global_winrate = 50 # % Thắng của khách
        self.rut_ao_enabled = False
        self.giftcodes = {}

state = BotState()

class Database:
    def __init__(self):
        self.users = {}
    def get_user(self, uid, name="Người chơi"):
        if uid not in self.users:
            self.users[uid] = {'balance': 100000, 'name': name, 'is_banned': False}
        return self.users[uid]
    def update_balance(self, uid, amount):
        user = self.get_user(uid)
        user['balance'] += amount
        return user['balance']

db = Database()

# ==========================================
# 🎲 2. GAME LOGIC (CÓ ÉP WINRATE)
# ==========================================
def play_game(choice, wr):
    dices = [random.randint(1, 6) for _ in range(3)]
    # Nếu xui (ngẫu nhiên > wr) thì ép cho kết quả ngược lại với khách đặt
    if random.randint(1, 100) > wr:
        if choice == "tai": dices = [1, 2, 2] 
        else: dices = [5, 5, 6]
    
    total = sum(dices)
    res_text = "tai" if total >= 11 else "xiu"
    icons = {1: "1️⃣", 2: "2️⃣", 3: "3️⃣", 4: "4️⃣", 5: "5️⃣", 6: "6️⃣"}
    return dices, [icons[d] for d in dices], total, res_text

# ==========================================
# 🤖 3. GIAO DIỆN CHÍNH
# ==========================================
def start(update: Update, context: CallbackContext):
    uid = update.effective_user.id
    user = db.get_user(uid, update.effective_user.first_name)
    
    msg = "💎 **CASINO TRÙM TÀI XỈU** 💎\n\n💰 Uy tín tạo nên thương hiệu!"
    
    # Menu cho người chơi
    kb = [
        [KeyboardButton("🎲 TÀI XỈU VIP"), KeyboardButton("🎁 NHẬP GIFTCODE")],
        [KeyboardButton("👤 CÁ NHÂN"), KeyboardButton("💸 RÚT TIỀN")]
    ]
    
    # CHỈ HIỆN NÚT NÀY NẾU LÀ ADMIN
    if uid == ADMIN_ID:
        kb.append([KeyboardButton("🛠 ADMIN PANEL")])
        msg += "\n\n⚠️ *Chào Sếp! Menu quản lý đã sẵn sàng.*"
        
    update.message.reply_text(msg, reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True), parse_mode=ParseMode.MARKDOWN)

def handle_text(update: Update, context: CallbackContext):
    uid = update.effective_user.id
    text = update.message.text
    user = db.get_user(uid)

    if text == "🎲 TÀI XỈU VIP":
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("10K", callback_data="bet_10000"), InlineKeyboardButton("50K", callback_data="bet_50000")],
            [InlineKeyboardButton("100K", callback_data="bet_100000"), InlineKeyboardButton("500K", callback_data="bet_500000")]
        ])
        update.message.reply_text(f"🎲 **TÀI XỈU ĐẲNG CẤP**\n💰 Ví: `{user['balance']:,.0f}đ`", reply_markup=kb, parse_mode=ParseMode.MARKDOWN)

    elif text == "🛠 ADMIN PANEL" and uid == ADMIN_ID:
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton(f"📈 Winrate: {state.global_winrate}%", callback_data="adm_wr")],
            [InlineKeyboardButton("✅ Bật Rút Ảo", callback_data="adm_on"), InlineKeyboardButton("❌ Tắt Rút Ảo", callback_data="adm_off")],
            [InlineKeyboardButton("🎁 Tạo Code 50k", callback_data="adm_gen")],
            [InlineKeyboardButton("📊 Thống Kê Bot", callback_data="adm_stats")]
        ])
        update.message.reply_text("🛠 **HỆ THỐNG QUẢN TRỊ**\nSếp muốn điều chỉnh gì?", reply_markup=kb)

    elif text == "🎁 NHẬP GIFTCODE":
        context.user_data['waiting_code'] = True
        update.message.reply_text("👉 Nhập mã code sếp phát:")

    # Xử lý nhập code
    elif context.user_data.get('waiting_code'):
        code = text.strip().upper()
        context.user_data['waiting_code'] = False
        if code in state.giftcodes:
            gc = state.giftcodes[code]
            if uid in gc['used'] or len(gc['used']) >= gc['limit']:
                update.message.reply_text("❌ Mã hết lượt hoặc sếp đã dùng!")
            else:
                gc['used'].append(uid)
                db.update_balance(uid, gc['amount'])
                update.message.reply_text(f"✅ Húp mạnh! +{gc['amount']:,.0f}đ")
        else:
            update.message.reply_text("❌ Code lỏ rồi sếp!")

# ==========================================
# ⚡ 4. XỬ LÝ NÚT BẤM
# ==========================================
def handle_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    data = query.data
    uid = query.from_user.id
    query.answer()

    if data.startswith("bet_"):
        amt = int(data.split("_")[1])
        kb = InlineKeyboardMarkup([[
            InlineKeyboardButton("🔴 TÀI (x1.95)", callback_data=f"p_tai_{amt}"),
            InlineKeyboardButton("⚫️ XỈU (x1.95)", callback_data=f"p_xiu_{amt}")
        ]])
        query.edit_message_text(f"💰 Cược: `{amt:,.0f}đ`\n👇 Chọn cửa:", reply_markup=kb, parse_mode=ParseMode.MARKDOWN)

    elif data.startswith("p_"):
        _, side, amt = data.split("_")
        amt = int(amt)
        user = db.get_user(uid)
        
        if user['balance'] < amt:
            return query.edit_message_text("❌ Tiền đâu mà đánh sếp?")

        db.update_balance(uid, -amt)
        _, icons, total, res_text = play_game(side, state.global_winrate)
        
        is_win = (side == res_text)
        if is_win:
            win_amt = int(amt * 1.95)
            db.update_balance(uid, win_amt)
            status = f"🎉 THẮNG: +{win_amt:,.0f}đ"
        else:
            status = "💀 THUA (Gà)"

        msg = (f"🎲 Kết quả: {' '.join(icons)} = {total} ({res_text.upper()})\n"
               f"💰 Cược: {side.upper()} | {status}\n"
               f"💵 Ví: `{user['balance']:,.0f}đ`")
        query.edit_message_text(msg, parse_mode=ParseMode.MARKDOWN)

    # ADMIN CALLBACKS
    elif uid == ADMIN_ID:
        if data == "adm_wr":
            # Xoay vòng winrate 10% -> 30% -> 50% -> 70% -> 90%
            state.global_winrate = 10 if state.global_winrate >= 90 else state.global_winrate + 20
            query.edit_message_text(f"✅ Đã chỉnh Winrate khách lên: {state.global_winrate}%", reply_markup=query.message.reply_markup)
        elif data == "adm_on":
            state.rut_ao_enabled = True
            query.edit_message_text("✅ Đã BẬT spam rút tiền ảo!", reply_markup=query.message.reply_markup)
        elif data == "adm_off":
            state.rut_ao_enabled = False
            query.edit_message_text("❌ Đã TẮT spam rút tiền ảo!", reply_markup=query.message.reply_markup)
        elif data == "adm_gen":
            new_c = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
            state.giftcodes[new_c] = {'amount': 50000, 'limit': 20, 'used': []}
            query.message.reply_text(f"🎁 **CODE MỚI ĐÃ TẠO**\nMã: `{new_c}`\nGiá trị: 50k\nLượt: 20")

# ==========================================
# 💸 5. VÒNG LẶP RÚT ẢO (LÙA GÀ)
# ==========================================
def auto_spam(context: CallbackContext):
    if not state.rut_ao_enabled: return
    names = ["Nguyễn ***", "Trần ***", "Lê ***", "Phạm ***", "Võ ***"]
    banks = ["MBBank", "Momo", "Vietcombank", "Techcombank"]
    amts = ["200,000", "500,000", "1,200,000", "3,000,000"]
    
    msg = (f"💸 **LỆNH RÚT THÀNH CÔNG**\n"
           f"👤 Khách: `{random.choice(names)}`\n"
           f"💰 Số tiền: `{random.choice(amts)}đ`\n"
           f"🏦 Bank: {random.choice(banks)}\n"
           f"⚡️ Trạng thái: **Thành công (1s)**")
    try: context.bot.send_message(chat_id=GROUP_ID, text=msg, parse_mode=ParseMode.MARKDOWN)
    except: pass

# ==========================================
# 🚀 6. RUN
# ==========================================
def main():
    updater = Updater(BOT_TOKEN, use_context=True)
    dp = updater.dispatcher
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_text))
    dp.add_handler(CallbackQueryHandler(handle_callback))
    
    # Spam mỗi 2 phút
    updater.job_queue.run_repeating(auto_spam, interval=120, first=10)

    print("🚀 BOT ADMIN ĐÃ LÊN SÀN!")
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
            
