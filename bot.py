import os
import json
import asyncio
from flask import Flask, render_template
from threading import Thread
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, CommandObject
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton, WebAppInfo

# --- CẤU HÌNH ---
TOKEN = "TOKEN_BOT_CUA_BAN"
ADMIN_ID = 12345678  # ID Telegram của bạn
REQUIRED_GROUPS = ["@ten_nhom_ban"] # Group bắt buộc
LOG_GROUP_ID = -100xxxxxxxx # Nhóm thông báo rút tiền thành công
MIN_WITHDRAW = 5000
REF_BONUS = 800
WEB_APP_URL = "https://your-app-on-render.onrender.com" # Link Render của bạn

app = Flask(__name__)
bot = Bot(token=TOKEN)
dp = Dispatcher()

# Database giả lập (Nên dùng MongoDB để lưu vĩnh viễn)
db = {"users": {}, "ips": {}} 

# --- WEB SERVER (CHO RENDER) ---
@app.route('/')
def index():
    return render_template('index.html')

# --- HÀM HỖ TRỢ ---
async def check_joined(user_id):
    for group in REQUIRED_GROUPS:
        try:
            member = await bot.get_chat_member(chat_id=group, user_id=user_id)
            if member.status in ['left', 'kicked']: return False
        except: return False
    return True

def get_main_menu():
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="👤 Tài khoản"), KeyboardButton(text="👨‍👩‍👧‍👦 Mời bạn")],
        [KeyboardButton(text="💰 Rút tiền")]
    ], resize_keyboard=True)

# --- XỬ LÝ BOT ---
@dp.message(Command("start"))
async def start_cmd(message: types.Message, command: CommandObject):
    user_id = message.from_user.id
    
    if user_id not in db["users"]:
        ref_id = command.args if command.args and command.args.isdigit() else None
        db["users"][user_id] = {'bal': 0, 'ip': None, 'ref_by': ref_id, 'banned': False}

    if db["users"][user_id]['banned']:
        return await message.answer("🚫 Tài khoản của bạn đã bị khóa!")

    # Bước 1: Check tham gia nhóm
    if not await check_joined(user_id):
        kb = [[InlineKeyboardButton(text="Tham gia Nhóm", url=f"https://t.me/{REQUIRED_GROUPS[0][1:]}")],
              [InlineKeyboardButton(text="🔄 Tôi đã tham gia", callback_data="check_step1")]]
        return await message.answer("❌ Bạn chưa tham gia nhóm bắt buộc!", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

    # Bước 2: Check IP
    if not db["users"][user_id]['ip']:
        kb = [[InlineKeyboardButton(text="📱 Xác thực IP thiết bị", web_app=WebAppInfo(url=WEB_APP_URL))]]
        return await message.answer("⚠️ Bước cuối: Vui lòng xác thực IP để bắt đầu.", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

    await message.answer("✅ Hệ thống đã sẵn sàng!", reply_markup=get_main_menu())

@dp.callback_query(F.data == "check_step1")
async def step1_callback(call: types.CallbackQuery):
    if await check_joined(call.from_user.id):
        await call.message.delete()
        await start_cmd(call.message, CommandObject(args=None))
    else:
        await call.answer("❌ Bạn vẫn chưa tham gia nhóm!", show_alert=True)

@dp.message(F.content_type == types.ContentType.WEB_APP_DATA)
async def handle_ip_data(message: types.Message):
    data = json.loads(message.web_app_data.data)
    user_id = message.from_user.id
    ip = data['ip']

    # Kiểm tra IP nghiêm ngặt
    if ip in db["ips"] and db["ips"][ip] != user_id:
        db["users"][user_id]['banned'] = True
        await message.answer(f"🚫 IP {ip} trùng lặp! Bạn đã bị BAN.")
        await bot.send_message(ADMIN_ID, f"📢 Cảnh báo: User {user_id} trùng IP {ip} với {db["ips"][ip]}")
        return

    db["users"][user_id]['ip'] = ip
    db["ips"][ip] = user_id
    
    # Cộng tiền cho người mời
    ref_by = db["users"][user_id]['ref_by']
    if ref_by and int(ref_by) in db["users"]:
        db["users"][int(ref_by)]['bal'] += REF_BONUS
        await bot.send_message(int(ref_by), f"🎉 Bạn được +{REF_BONUS}đ từ bạn mới xác thực IP!")

    await message.answer(f"✅ Xác thực IP thành công: {ip}", reply_markup=get_main_menu())

@dp.message(F.text == "👤 Tài khoản")
async def info(message: types.Message):
    u = db["users"][message.from_user.id]
    await message.answer(f"💳 **ID:** `{message.from_user.id}`\n💰 **Số dư:** {u['bal']}đ\n🌐 **IP:** {u['ip']}", parse_mode="Markdown")

@dp.message(F.text == "👨‍👩‍👧‍👦 Mời bạn")
async def invite(message: types.Message):
    link = f"https://t.me/{(await bot.get_me()).username}?start={message.from_user.id}"
    await message.answer(f"🎁 Nhận {REF_BONUS}đ/bạn\n\nLink: `{link}`", parse_mode="Markdown")

@dp.message(F.text == "💰 Rút tiền")
async def withdraw(message: types.Message):
    u = db["users"][message.from_user.id]
    if u['bal'] < MIN_WITHDRAW:
        return await message.answer(f"❌ Cần tối thiểu {MIN_WITHDRAW}đ.")
    
    kb = [[InlineKeyboardButton(text="✅ Duyệt", callback_data=f"pay_{message.from_user.id}_{u['bal']}"),
           InlineKeyboardButton(text="🚫 Ban", callback_data=f"ban_{message.from_user.id}")]]
    await bot.send_message(ADMIN_ID, f"🔔 Đơn rút: {message.from_user.id}\nSố tiền: {u['bal']}đ\nIP: {u['ip']}", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
    await message.answer("⏳ Đã gửi yêu cầu rút tiền cho Admin.")

@dp.callback_query(F.data.startswith("pay_"))
async def admin_pay(call: types.CallbackQuery):
    _, uid, amt = call.data.split("_")
    uid = int(uid)
    db["users"][uid]['bal'] = 0
    await bot.send_message(uid, f"✅ Admin đã duyệt đơn rút {amt}đ của bạn!")
    await bot.send_message(LOG_GROUP_ID, f"✅ Rút thành công: ****{str(uid)[-4:]} | +{amt}đ")
    await call.message.edit_text(f"✅ Đã duyệt đơn {amt}đ cho {uid}")

@dp.callback_query(F.data.startswith("ban_"))
async def admin_ban(call: types.CallbackQuery):
    uid = int(call.data.split("_")[1])
    db["users"][uid]['banned'] = True
    await call.answer("Đã Ban người dùng.")
    await call.message.edit_text(f"🚫 Đã BAN user {uid}")

# --- KHỞI CHẠY ---
def run_flask():
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))

async def main():
    Thread(target=run_flask).start()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
  
