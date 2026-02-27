import asyncio
import logging
import os
from telethon import TelegramClient, events
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, CallbackQueryHandler, MessageHandler, filters

# --- CẤU HÌNH ---
API_ID = 36437338  
API_HASH = '18d34c7efc396d277f3db62baa078efc' 
SESSION_DIR = 'sessions' 
BOT_TOKEN = '8499499024:AAFSifEjBAKL2BSmanDDlXuRGh93zvZjM78' 
ADMIN_ID = 7816353760  

if not os.path.exists(SESSION_DIR):
    os.makedirs(SESSION_DIR)

# --- BIẾN TOÀN CỤC ---
spam_content = "⚡️ DỊCH VỤ TĂNG MEM NHÓM GIÁ RẺ - NHẮN TIN NGAY ⚡️"
trigger_keyword = "bot"
groups_to_spam = [] 
is_spamming = False
active_clients = {} 
stats = {"sent": 0, "replied": 0}
SPAM_INTERVAL = 300 # 5 phút

# --- LOGGING ---
logging.basicConfig(level=logging.INFO)

# --- QUẢN LÝ TÀI KHOẢN ---
async def load_sessions():
    """Khởi động tất cả các session đã có"""
    for filename in os.listdir(SESSION_DIR):
        if filename.endswith(".session"):
            session_path = os.path.join(SESSION_DIR, filename[:-8])
            client = TelegramClient(session_path, API_ID, API_HASH)
            await client.connect()
            if await client.is_user_authorized():
                active_clients[filename] = client
                logging.info(f"✅ Đã tải: {filename}")
                
                # Tự trả lời
                @client.on(events.NewMessage(chats=groups_to_spam))
                async def handler(event):
                    if trigger_keyword.lower() in event.raw_text.lower():
                        await event.reply(spam_content)
                        stats["replied"] += 1
            else:
                logging.error(f"❌ {filename} chưa auth")

# --- THREAD CHẠY SPAM ---
async def spam_task():
    global is_spamming
    while is_spamming:
        for session_file, client in active_clients.items():
            if not is_spamming: break
            for group in groups_to_spam:
                try:
                    await client.send_message(group, spam_content)
                    stats["sent"] += 1
                    await asyncio.sleep(2) 
                except Exception as e:
                    logging.error(f"❌ {session_file} lỗi: {e}")
        
        if is_spamming:
            await asyncio.sleep(SPAM_INTERVAL)

# --- BOT ĐIỀU KHIỂN ---
def get_main_keyboard():
    keyboard = [
        [InlineKeyboardButton("🚀 Chạy Spam", callback_data='start'),
         InlineKeyboardButton("🛑 Dừng Spam", callback_data='stop')],
        [InlineKeyboardButton("📊 Thống kê", callback_data='stats')],
        [InlineKeyboardButton("➕ Nạp Acc Mới", callback_data='add_acc')]
    ]
    return InlineKeyboardMarkup(keyboard)

async def start_bot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    await update.message.reply_text("🤖 **BẢNG ĐIỀU KHIỂN** 🤖", reply_markup=get_main_keyboard(), parse_mode='Markdown')

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global is_spamming
    query = update.callback_query
    await query.answer()

    if query.data == 'start':
        if not is_spamming:
            is_spamming = True
            asyncio.create_task(spam_task())
            await query.edit_message_text("✅ Đã bắt đầu spam!", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Quay lại", callback_data='back')]]))
        else:
            await query.edit_message_text("⚠️ Đang chạy!", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Quay lại", callback_data='back')]]))

    elif query.data == 'stop':
        is_spamming = False
        await query.edit_message_text("🛑 Đã dừng.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Quay lại", callback_data='back')]]))

    elif query.data == 'stats':
        text = f"📊 **TK**\nAcc: {len(active_clients)}\nSent: {stats['sent']}\nRep: {stats['replied']}"
        await query.edit_message_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Quay lại", callback_data='back')]]))

    elif query.data == 'add_acc':
        context.user_data['action'] = 'phone'
        await query.edit_message_text("📱 **Gửi số điện thoại (vd: +84912345678):**", parse_mode='Markdown')
    
    elif query.data == 'back':
        await query.edit_message_text("🤖 **BẢNG ĐIỀU KHIỂN** 🤖", reply_markup=get_main_keyboard(), parse_mode='Markdown')

# --- LOGIC NẠP ACC QUA BOT ---
async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global active_clients
    if update.effective_user.id != ADMIN_ID: return

    action = context.user_data.get('action')

    if action == 'phone':
        phone = update.message.text
        context.user_data['phone'] = phone
        context.user_data['action'] = 'code'
        
        # Tạm thời tạo client để xin code
        session_name = os.path.join(SESSION_DIR, phone)
        client = TelegramClient(session_name, API_ID, API_HASH)
        await client.connect()
        context.user_data['client'] = client
        
        # Gửi yêu cầu code
        sent_code = await client.send_code_request(phone)
        context.user_data['phone_code_hash'] = sent_code.phone_code_hash
        
        await update.message.reply_text("🔑 **Đã gửi mã về Telegram, gửi mã cho tôi:**", parse_mode='Markdown')

    elif action == 'code':
        code = update.message.text
        client = context.user_data['client']
        phone = context.user_data['phone']
        
        try:
            await client.sign_in(phone, code, phone_code_hash=context.user_data['phone_code_hash'])
            await update.message.reply_text("✅ **Nạp acc thành công!** Hãy restart bot để áp dụng.", reply_markup=get_main_keyboard())
            active_clients[phone] = client
            context.user_data['action'] = None
        except Exception as e:
            await update.message.reply_text(f"❌ Lỗi: {e}")

# --- KHỞI TẠO ---
async def main():
    await load_sessions()
    application = ApplicationBuilder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start_bot))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
    
    await application.initialize()
    await application.start()
    await application.updater.start_polling()
    await asyncio.Event().wait()

if __name__ == '__main__':
    asyncio.run(main())
    
