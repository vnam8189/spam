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

# --- KHỞI TẠO THƯ MỤC SESSION ---
if not os.path.exists(SESSION_DIR):
    os.makedirs(SESSION_DIR)

# --- BIẾN TOÀN CỤC ---
spam_content = "⚡️ DỊCH VỤ TĂNG MEM NHÓM GIÁ RẺ - NHẮN TIN NGAY ⚡️"
trigger_keyword = "bot"
groups_to_spam = [] 
is_spamming = False
active_clients = {} 
stats = {"sent": 0, "replied": 0}

# --- LOGGING ---
logging.basicConfig(level=logging.INFO)

# --- QUẢN LÝ TÀI KHOẢN ---
async def load_sessions():
    """Khởi động tất cả các session có trong thư mục sessions/"""
    for filename in os.listdir(SESSION_DIR):
        if filename.endswith(".session"):
            session_name = os.path.join(SESSION_DIR, filename[:-8])
            client = TelegramClient(session_name, API_ID, API_HASH)
            await client.start()
            active_clients[filename] = client
            logging.info(f"✅ Đã tải: {filename}")
            
            # Đăng ký tự động trả lời
            @client.on(events.NewMessage(chats=groups_to_spam))
            async def handler(event):
                if trigger_keyword.lower() in event.raw_text.lower():
                    await event.reply(spam_content)
                    stats["replied"] += 1
                    logging.info(f"⚡ Rep tự động: {event.chat_id}")

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
                    logging.info(f"📤 [{session_file}] Gửi tới {group}")
                    await asyncio.sleep(60) # Chống ban
                except Exception as e:
                    logging.error(f"❌ [{session_file}] Lỗi: {e}")
                    await asyncio.sleep(5)

# --- BOT ĐIỀU KHIỂN (UI) ---
async def start_bot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    
    keyboard = [
        [InlineKeyboardButton("🚀 Chạy Spam", callback_data='start'),
         InlineKeyboardButton("🛑 Dừng Spam", callback_data='stop')],
        [InlineKeyboardButton("📊 Thống kê", callback_data='stats')],
        [InlineKeyboardButton("📝 Quản lý Nội dung", callback_data='edit_content')],
        [InlineKeyboardButton("👥 Quản lý Nhóm", callback_data='edit_groups')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("🤖 **BẢNG ĐIỀU KHIỂN USERBOT** 🤖", reply_markup=reply_markup, parse_mode='Markdown')

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global is_spamming, spam_content, groups_to_spam
    query = update.callback_query
    await query.answer()

    if query.data == 'start':
        if not is_spamming:
            is_spamming = True
            asyncio.create_task(spam_task())
            await query.edit_message_text("✅ Đã bắt đầu spam!", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Quay lại", callback_data='back')]]))
        else:
            await query.edit_message_text("⚠️ Đang chạy rồi!", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Quay lại", callback_data='back')]]))

    elif query.data == 'stop':
        is_spamming = False
        await query.edit_message_text("🛑 Đã dừng spam.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Quay lại", callback_data='back')]]))

    elif query.data == 'stats':
        status = "🟢 Đang chạy" if is_spamming else "🔴 Đã dừng"
        stats_text = (
            f"📊 **THỐNG KÊ CHI TIẾT**\n\n"
            f"Trạng thái: {status}\n"
            f"Số acc hoạt động: {len(active_clients)}\n"
            f"Tổng tin đã gửi: {stats['sent']}\n"
            f"Tổng tự rep: {stats['replied']}\n"
            f"Số nhóm cần spam: {len(groups_to_spam)}"
        )
        await query.edit_message_text(stats_text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Quay lại", callback_data='back')]]))

    elif query.data == 'edit_content':
        keyboard = [
            [InlineKeyboardButton("👀 Xem Nội Dung", callback_data='view_content')],
            [InlineKeyboardButton("✍️ Sửa Nội Dung", callback_data='input_content')],
            [InlineKeyboardButton("🔙 Quay lại", callback_data='back')]
        ]
        await query.edit_message_text("📝 **QUẢN LÝ NỘI DUNG**", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

    elif query.data == 'view_content':
        await query.edit_message_text(f"📖 **Nội dung hiện tại:**\n\n{spam_content}", parse_mode='Markdown', reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Quay lại", callback_data='edit_content')]]))

    elif query.data == 'input_content':
        context.user_data['action'] = 'set_content'
        await query.edit_message_text("✍️ **Gửi tin nhắn mới để đặt làm nội dung spam/trả lời:**", parse_mode='Markdown')

    elif query.data == 'edit_groups':
        context.user_data['action'] = 'set_groups'
        await query.edit_message_text("📝 **Gửi danh sách nhóm (mỗi nhóm 1 dòng, ví dụ @username):**", parse_mode='Markdown')
    
    elif query.data == 'back':
        await start_bot(query, context)

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global spam_content, groups_to_spam
    if update.effective_user.id != ADMIN_ID: return

    action = context.user_data.get('action')
    if action == 'set_content':
        spam_content = update.message.text
        await update.message.reply_text("✅ Đã cập nhật nội dung mới!")
        context.user_data['action'] = None
    elif action == 'set_groups':
        groups_to_spam = update.message.text.split('\n')
        await update.message.reply_text(f"✅ Đã cập nhật {len(groups_to_spam)} nhóm!")
        context.user_data['action'] = None

# --- KHỞI TẠO HỆ THỐNG ---
async def main():
    # 1. Tải tất cả acc từ thư mục sessions/
    await load_sessions()

    # 2. Khởi động Bot điều khiển
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
    
