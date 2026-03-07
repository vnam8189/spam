import os
from flask import Flask, render_template
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQuery_Handler

# Cấu hình
TOKEN = "TOKEN_BOT_CUA_BAN"
ADMIN_ID = 12345678  # Thay bằng ID của bạn
REQUIRED_GROUPS = ["@ten_nhom_1"] # Admin có thể sửa trong code hoặc DB
MIN_WITHDRAW = 5000
REF_BONUS = 800

app = Flask(__name__)
db_users = {} # {user_id: {'bal': 0, 'ip': None, 'ref_by': None, 'banned': False}}
db_ips = {}   # {ip: user_id}

# --- WEB SERVER CHO RENDER ---
@app.route('/')
def index():
    return render_template('index.html')

# --- LOGIC BOT ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    
    if user_id not in db_users:
        # Xử lý mời bạn (t.me/bot?start=123)
        ref_id = context.args[0] if context.args else None
        db_users[user_id] = {'bal': 0, 'ip': None, 'ref_by': ref_id, 'banned': False}

    # Bước 1: Check Group
    is_member = await check_join(user_id, context)
    if not is_member:
        keyboard = [[InlineKeyboardButton("Tham gia ngay", url=f"https://t.me/{REQUIRED_GROUPS[0][1:]}")],
                    [InlineKeyboardButton("🔄 Tôi đã tham gia", callback_data="check_step1")]]
        await update.message.reply_text("❌ Bạn phải vào nhóm để tiếp tục!", reply_markup=InlineKeyboardMarkup(keyboard))
        return

    # Bước 2: Check IP (Nếu đã vào nhóm)
    await show_ip_step(update, user_id)

async def check_join(user_id, context):
    try:
        member = await context.bot.get_chat_member(chat_id=REQUIRED_GROUPS[0], user_id=user_id)
        return member.status not in ['left', 'kicked', 'deleted']
    except: return False

async def show_ip_step(update, user_id):
    if not db_users[user_id]['ip']:
        web_url = "URL_APP_CUA_BAN_TREN_RENDER" # Ví dụ: https://mybot.onrender.com
        keyboard = [[InlineKeyboardButton("📱 Xác thực IP", web_app=WebAppInfo(url=web_url))]]
        await update.message.reply_text("⚠️ Bước cuối: Nhấn nút dưới để xác thực IP thiết bị!", reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await show_main_menu(update)

async def show_main_menu(update):
    keyboard = [['👤 Tài khoản', '👨‍👩‍👧‍👦 Mời bạn'], ['💰 Rút tiền']]
    await update.message.reply_text("✅ Đã xác thực! Menu đã mở:", reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True))

# Xử lý dữ liệu từ Web App gửi về (Xác thực IP)
async def handle_web_app_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    import json
    data = json.loads(update.effective_message.web_app_data.data)
    user_id = data['user_id']
    ip = data['ip']

    # CHECK IP NGHIÊM NGẶT
    if ip in db_ips and db_ips[ip] != user_id:
        db_users[user_id]['banned'] = True
        await update.message.reply_text(f"🚫 Cảnh báo: IP {ip} đã được dùng bởi tài khoản khác. BẠN ĐÃ BỊ BAN!")
        await context.bot.send_message(ADMIN_ID, f"📢 User {user_id} bị BAN do trùng IP {ip} với User {db_ips[ip]}")
        return

    db_users[user_id]['ip'] = ip
    db_ips[ip] = user_id
    
    # Cộng tiền cho người mời sau khi xác thực IP thành công
    ref_by = db_users[user_id]['ref_by']
    if ref_by and int(ref_by) in db_users:
        db_users[int(ref_by)]['bal'] += REF_BONUS
        await context.bot.send_message(int(ref_by), f"🎉 Bạn được +{REF_BONUS}đ từ việc mời bạn mới!")

    await update.message.reply_text(f"✅ Xác thực thành công IP: {ip}")
    await show_main_menu(update)

# --- CHẠY SONG SONG BOT VÀ WEB ---
if __name__ == '__main__':
    from threading import Thread
    def run_bot():
        app_bot = Application.builder().token(TOKEN).build()
        app_bot.add_handler(CommandHandler("start", start))
        app_bot.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, handle_web_app_data))
        app_bot.run_polling()

    Thread(target=run_bot).start()
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
    
