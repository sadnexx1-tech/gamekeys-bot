import asyncio
import logging
import os
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import PreCheckoutQuery, FSInputFile
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
import aiosqlite
import requests
from yookassa import Configuration, Payment
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
YOOKASSA_SHOP_ID = os.getenv("YOOKASSA_SHOP_ID")
YOOKASSA_SECRET = os.getenv("YOOKASSA_SECRET")
ADMIN_ID = int(os.getenv("ADMIN_ID", 0))
TELEGRAM_CHANNEL_ID = int(os.getenv("-1001331881336", 0))
CHANNEL_USERNAME = "frexgamesl"
Configuration.account_id = YOOKASSA_SHOP_ID
Configuration.secret_key = YOOKASSA_SECRET
logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())
db_path = 'games.db'
PROMOS = {
"FREX2024": {"discount": 20, "active": True},
"NEWGAMER": {"discount": 15, "active": True},
"VK_FRIENDS": {"discount": 10, "active": True}
}
FREE_KEYS = {
"TESTKEY1": "GTA5-FREE-TEST-001",
"TESTKEY2": "CYBER-FREE-TEST-002"
}
class Form(StatesGroup):
selecting_game = State()
async def init_db():
async with aiosqlite.connect(db_path) as db:
await db.execute('''
CREATE TABLE IF NOT EXISTS games (
id INTEGER PRIMARY KEY AUTOINCREMENT,
name TEXT, description TEXT, price INTEGER,
photo_path TEXT, stock INTEGER DEFAULT 0, key TEXT
)
''')
await db.execute("INSERT OR IGNORE INTO games (id, name, description, price, photo_path, stock, key) VALUES (?, ?, ?, ?, ?, ?, ?)",
(1, "GTA V", "Открытый мир, экшн. Steam ключ. 🎮", 500, "images/gta.jpg", 10, "GTA5-ABC123-DEF"))
await db.execute("INSERT OR IGNORE INTO games (id, name, description, price, photo_path, stock, key) VALUES (?, ?, ?, ?, ?, ?, ?)",
(2, "Cyberpunk 2077", "RPG, киберпанк. 🌆 СКИДКА -20%", 400, "images/cyberpunk.jpg", 5, "CP2077-XYZ789"))
await db.execute("INSERT OR IGNORE INTO games (id, name, description, price, photo_path, stock, key) VALUES (?, ?, ?, ?, ?, ?, ?)",
(3, "Elden Ring", "Dark Fantasy Action RPG. 🏰 НОВОЕ", 600, "images/elden.jpg", 3, "ELDEN-RING-ABC"))
await db.commit()
async def check_subscription(user_id: int) -> bool:
try:
member = await bot.get_chat_member(chat_id=TELEGRAM_CHANNEL_ID, user_id=user_id)
return member.status in ["creator", "administrator", "member"]
except Exception as e:
logging.error(f"Subscription check error: {e}")
return False
def get_main_keyboard():
kb = types.ReplyKeyboardMarkup(
keyboard=[
[types.KeyboardButton(text="🛒 Каталог"), types.KeyboardButton(text="ℹ️ О нас")],
[types.KeyboardButton(text="🎁 Бесплатные ключи"), types.KeyboardButton(text="🎟️ Промокоды")],
[types.KeyboardButton(text="🔥 Акции"), types.KeyboardButton(text="📞 Поддержка")]
],
resize_keyboard=True
)
return kb
def get_subscription_keyboard():
kb = types.InlineKeyboardMarkup(inline_keyboard=[
[types.InlineKeyboardButton(text="📢 Подписаться на канал", url=f"https://t.me/{CHANNEL_USERNAME}")],
[types.InlineKeyboardButton(text="✅ Проверить подписку", callback_data="check_sub")]
])
return kb
@dp.message(CommandStart())
async def start(msg: types.Message):
user_id = msg.from_user.id
is_subscribed = await check_subscription(user_id)
if is_subscribed:
    kb = get_main_keyboard()
    await msg.answer(
        "🎮 **Добро пожаловать в FREX GAMES!**\n\n"
        "⚡ Дешевые ключи игр Steam 🔑\n"
        "🎁 Промокоды • Бесплатные раздачи\n\n"
        "Выберите действие ⬇️",
        reply_markup=kb,
        parse_mode="Markdown"
    )
else:
    kb = get_subscription_keyboard()
    await msg.answer(
        "🔒 **ТРЕБУЕТСЯ ПОДПИСКА НА КАНАЛ!**\n\n"
        "Для доступа ко всем функциям бота необходимо подписаться на наш Telegram канал.\n\n"
        "✨ После подписки нажми кнопку ниже ⬇️",
        reply_markup=kb,
        parse_mode="Markdown"
    )

@dp.callback_query(F.data == "check_sub")
async def check_subscription_callback(callback: types.CallbackQuery):
user_id = callback.from_user.id
is_subscribed = await check_subscription(user_id)
if is_subscribed:
    kb = get_main_keyboard()
    await callback.message.edit_text(
        "🎮 **Добро пожаловать в FREX GAMES!**\n\n"
        "⚡ Дешевые ключи игр Steam 🔑\n"
        "🎁 Промокоды • Бесплатные раздачи\n\n"
        "Выберите действие ⬇️",
        reply_markup=kb,
        parse_mode="Markdown"
    )
    await callback.answer("✅ Спасибо за подписку!", show_alert=False)
else:
    await callback.answer("❌ Вы ещё не подписаны на канал!", show_alert=True)

@dp.message(F.text == "ℹ️ О нас")
async def about_us(msg: types.Message):
is_subscribed = await check_subscription(msg.from_user.id)
if not is_subscribed:
    kb = get_subscription_keyboard()
    await msg.answer("🔒 Подпишись на канал, чтобы использовать бота!", reply_markup=kb)
    return

about_text = (
    "📌 **О компании FREX GAMES**\n\n"
    "✨ Лицензионные ключи Steam\n"
    "🔐 100% защита - все ключи официальные\n"
    "⚡ Мгновенная доставка\n"
    "🎁 Акции каждый день\n"
    "💬 Поддержка 24/7\n\n"
    "🔗 **Присоединяйтесь:**\n"
    "📱 Канал: @frexgames_channel"
)

kb = get_main_keyboard()
await msg.answer(about_text, reply_markup=kb, parse_mode="Markdown")

@dp.message(F.text == "🛒 Каталог")
async def show_catalog(msg: types.Message):
is_subscribed = await check_subscription(msg.from_user.id)
if not is_subscribed:
    kb = get_subscription_keyboard()
    await msg.answer("🔒 Подпишись на канал, чтобы использовать бота!", reply_markup=kb)
    return

async with aiosqlite.connect(db_path) as db:
    cursor = await db.execute("SELECT id, name, price, stock FROM games WHERE stock > 0")
    games = await cursor.fetchall()

if not games:
    await msg.answer("❌ Товары закончились.")
    return

text = "📦 **КАТАЛОГ:**\n\n"
kb_inline = types.InlineKeyboardMarkup(inline_keyboard=[])

for game in games:
    text += f"🎮 **{game[1]}** — {game[2]}₽ ({game[3]} шт)\n"
    kb_inline.inline_keyboard.append([
        types.InlineKeyboardButton(text=f"Купить {game[1]}", callback_data=f"buy_{game[0]}")
    ])

text += "\n💡 **Совет:** Используй промокод для скидки!"

await msg.answer(text, reply_markup=kb_inline, parse_mode="Markdown")

@dp.message(F.text == "🎁 Бесплатные ключи")
async def free_keys(msg: types.Message):
is_subscribed = await check_subscription(msg.from_user.id)
if not is_subscribed:
    kb = get_subscription_keyboard()
    await msg.answer("🔒 Подпишись на канал!", reply_markup=kb)
    return

free_text = (
    "🎁 **БЕСПЛАТНЫЕ КЛЮЧИ**\n\n"
    "✅ Test Game Key #1\n"
    "✅ Test Game Key #2\n\n"
    "Нажми кнопку ниже! ⬇️"
)

kb = types.InlineKeyboardMarkup(inline_keyboard=[
    [types.InlineKeyboardButton(text="🎁 Получить", callback_data="get_free_key")],
    [types.InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_menu")]
])

await msg.answer(free_text, reply_markup=kb, parse_mode="Markdown")

@dp.message(F.text == "🎟️ Промокоды")
async def promos(msg: types.Message):
is_subscribed = await check_subscription(msg.from_user.id)
if not is_subscribed:
    kb = get_subscription_keyboard()
    await msg.answer("🔒 Подпишись на канал!", reply_markup=kb)
    return

promo_text = (
    "🎟️ **АКТИВНЫЕ ПРОМОКОДЫ:**\n\n"
    "✅ **FREX2024** — 20% скидка\n"
    "✅ **NEWGAMER** — 15% скидка\n"
    "✅ **VK_FRIENDS** — 10% скидка\n\n"
    "💡 Напиши промокод при покупке!"
)

kb = types.InlineKeyboardMarkup(inline_keyboard=[
    [types.InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_menu")]
])

await msg.answer(promo_text, reply_markup=kb, parse_mode="Markdown")

@dp.message(F.text == "🔥 Акции")
async def sales(msg: types.Message):
is_subscribed = await check_subscription(msg.from_user.id)
if not is_subscribed:
    kb = get_subscription_keyboard()
    await msg.answer("🔒 Подпишись на канал!", reply_markup=kb)
    return

sales_text = (
    "🔥 **ГОРЯЧИЕ АКЦИИ:**\n\n"
    "⚡ Cyberpunk 2077 — -20%\n"
    "💎 Elden Ring — НОВИНКА\n"
    "🎯 Каждый 3-й ключ -10%\n\n"
    "⏰ Обновляется ежедневно!"
)

kb = types.InlineKeyboardMarkup(inline_keyboard=[
    [types.InlineKeyboardButton(text="🛒 К каталогу", callback_data="go_catalog")],
    [types.InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_menu")]
])

await msg.answer(sales_text, reply_markup=kb, parse_mode="Markdown")

@dp.message(F.text == "📞 Поддержка")
async def support(msg: types.Message):
is_subscribed = await check_subscription(msg.from_user.id)
if not is_subscribed:
    kb = get_subscription_keyboard()
    await msg.answer("🔒 Подпишись на канал!", reply_markup=kb)
    return

support_text = (
    "📞 **СЛУЖБА ПОДДЕРЖКИ**\n\n"
    "❓ **Как активировать?**\n"
    "Steam → Games → Activate Product\n\n"
    "❓ **Ключ не работает?**\n"
    "Напиши: @sadnexxbruh\n\n"
    "❓ **Возврат?**\n"
    "24 часа, если не активирован"
)

kb = get_main_keyboard()
await msg.answer(support_text, reply_markup=kb, parse_mode="Markdown")

@dp.callback_query(F.data == "back_to_menu")
async def back_to_menu(callback: types.CallbackQuery):
kb = get_main_keyboard()
await callback.message.edit_text(
"🎮 ГЛАВНОЕ МЕНЮ",
reply_markup=kb,
parse_mode="Markdown"
)
await callback.answer()
@dp.callback_query(F.data == "get_free_key")
async def get_free_key(callback: types.CallbackQuery):
import random
free_key = random.choice(["GTA5-FREE-TEST-001", "CYBER-FREE-TEST-002"])
await callback.message.answer(
    f"🎉 **Ты получил бесплатный ключ!**\n\n"
    f"🔑 `{free_key}`\n\n"
    f"Активируй в Steam: https://store.steampowered.com/account/registerkey",
    parse_mode="Markdown"
)

await callback.answer("✅ Ключ отправлен!")

@dp.callback_query(F.data == "go_catalog")
async def go_catalog(callback: types.CallbackQuery):
await callback.answer()
await show_catalog(callback.message)
@dp.callback_query(F.data.startswith("buy_"))
async def process_buy(callback: types.CallbackQuery, state: FSMContext):
game_id = int(callback.data.split("_")[1])
async with aiosqlite.connect(db_path) as db:
    cursor = await db.execute(
        "SELECT name, description, price, photo_path, key FROM games WHERE id=? AND stock > 0",
        (game_id,)
    )
    game = await cursor.fetchone()

if not game:
    await callback.answer("❌ Товар закончился!", show_alert=True)
    return

name, description, price, photo_path, key = game

await state.update_data(
    game_id=game_id,
    game_name=name,
    game_key=key,
    game_price=price
)

try:
    photo = FSInputFile(photo_path)
    await callback.message.answer_photo(
        photo=photo,
        caption=f"🎮 **{name}**\n{description}\n💰 **{price}₽**",
        parse_mode="Markdown"
    )
except:
    await callback.message.answer(f"🎮 **{name}**\n{description}\n💰 **{price}₽**")

kb = types.InlineKeyboardMarkup(inline_keyboard=[
    [types.InlineKeyboardButton(text="💳 Оплатить", callback_data=f"pay_{game_id}")],
    [types.InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_menu")]
])

await callback.message.answer("Выберите действие ⬇️", reply_markup=kb)
await callback.answer()

@dp.callback_query(F.data.startswith("pay_"))
async def create_payment(callback: types.CallbackQuery, state: FSMContext):
game_id = int(callback.data.split("_")[1])
data = await state.get_data()
game_name = data.get("game_name", "Game")
game_key = data.get("game_key", "")
game_price = data.get("game_price", 100)

try:
    payment = Payment.create({
        "amount": {
            "value": str(game_price),
            "currency": "RUB"
        },
        "confirmation": {
            "type": "redirect",
            "return_url": "https://t.me/frexgames_bot"
        },
        "description": f"Покупка: {game_name}",
        "receipt": {
            "email": "support@frexgames.ru",
            "items": [
                {
                    "description": game_name,
                    "quantity": "1.00",
                    "amount": {
                        "value": str(game_price),
                        "currency": "RUB"
                    },
                    "vat_code": 1
                }
            ]
        }
    })
    
    payment_url = payment.confirmation.confirmation_url
    
    kb = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="💳 Оплатить", url=payment_url)],
        [types.InlineKeyboardButton(text="✅ Я оплатил", callback_data=f"confirm_pay_{game_id}")],
        [types.InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_menu")]
    ])
    
    await callback.message.answer(
        f"💳 **ОПЛАТА**\n\n"
        f"Товар: {game_name}\n"
        f"Сумма: {game_price}₽\n\n"
        f"🔗 Нажми кнопку ниже для оплаты →",
        reply_markup=kb,
        parse_mode="Markdown"
    )
    
    await callback.answer()
    
except Exception as e:
    logging.error(f"Payment error: {e}")
    await callback.answer("❌ Ошибка создания платежа", show_alert=True)

@dp.callback_query(F.data.startswith("confirm_pay_"))
async def confirm_payment(callback: types.CallbackQuery, state: FSMContext):
game_id = int(callback.data.split("_")[2])
data = await state.get_data()
game_key = data.get("game_key", "")
game_name = data.get("game_name", "Game")

async with aiosqlite.connect(db_path) as db:
    await db.execute("UPDATE games SET stock = stock - 1 WHERE id=?", (game_id,))
    await db.commit()

await callback.message.answer(
    f"✅ **СПАСИБО ЗА ПОКУПКУ!**\n\n"
    f"🎮 {game_name}\n"
    f"🔑 Ваш ключ:\n`{game_key}`\n\n"
    f"📝 **Активация:**\n"
    f"Steam → Games → Activate Product\n\n"
    f"❓ Проблема? @sadnexxbruh",
    parse_mode="Markdown"
)

await state.clear()
await callback.answer("✅ Спасибо!")

async def main():
await init_db()
await dp.start_polling(bot)
if name == "main":
asyncio.run(main())

