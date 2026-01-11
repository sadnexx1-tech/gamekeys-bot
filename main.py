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
from yookassa import Configuration, Payment

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
YOOKASSA_SHOP_ID = os.getenv("YOOKASSA_SHOP_ID")
YOOKASSA_SECRET = os.getenv("YOOKASSA_SECRET")
ADMIN_ID = int(os.getenv("ADMIN_ID", 0))
TELEGRAM_CHANNEL_ID = int(os.getenv("TELEGRAM_CHANNEL_ID", 0))
CHANNEL_USERNAME = "your_channel_name"  # ЗАМЕНИ НА СВОЙ КАНАЛ!

Configuration.account_id = YOOKASSA_SHOP_ID
Configuration.secret_key = YOOKASSA_SECRET

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())
db_path = 'games.db'

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
                         (1, "GTA V", "Открытый мир, экшн. Steam ключ 🎮", 500, "images/gta.jpg", 10, "GTA5-ABC123-DEF"))
        await db.execute("INSERT OR IGNORE INTO games (id, name, description, price, photo_path, stock, key) VALUES (?, ?, ?, ?, ?, ?, ?)",
                         (2, "Cyberpunk 2077", "RPG, киберпанк 🌆", 400, "images/cyberpunk.jpg", 5, "CP2077-XYZ789"))
        await db.execute("INSERT OR IGNORE INTO games (id, name, description, price, photo_path, stock, key) VALUES (?, ?, ?, ?, ?, ?, ?)",
                         (3, "Elden Ring", "Dark Fantasy RPG 🏰", 600, "images/elden.jpg", 3, "ELDEN-RING-ABC"))
        await db.commit()

async def check_subscription(user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(chat_id=TELEGRAM_CHANNEL_ID, user_id=user_id)
        return member.status in ["creator", "administrator", "member"]
    except:
        return False

@dp.message(CommandStart())
async def start(msg: types.Message):
    user_id = msg.from_user.id
    is_subscribed = await check_subscription(user_id)
    
    if is_subscribed:
        kb = types.ReplyKeyboardMarkup(
            keyboard=[
                [types.KeyboardButton(text="🛒 Каталог"), types.KeyboardButton(text="ℹ️ О нас")],
                [types.KeyboardButton(text="🎁 Бесплатные ключи"), types.KeyboardButton(text="🔥 Акции")],
            ],
            resize_keyboard=True
        )
        await msg.answer("🎮 **Добро пожаловать!**\n⚡ Дешевые ключи Steam 🔑", reply_markup=kb, parse_mode="Markdown")
    else:
        kb = types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text="📢 Подписаться", url=f"https://t.me/{CHANNEL_USERNAME}")],
            [types.InlineKeyboardButton(text="✅ Проверить", callback_data="check_sub")]
        ])
        await msg.answer("🔒 Подпишись на канал!", reply_markup=kb)

@dp.callback_query(F.data == "check_sub")
async def check_sub(callback: types.CallbackQuery):
    is_subscribed = await check_subscription(callback.from_user.id)
    if is_subscribed:
        await callback.answer("✅ Спасибо!")
        await start(callback.message)
    else:
        await callback.answer("❌ Не подписан!", show_alert=True)

@dp.message(F.text == "🛒 Каталог")
async def catalog(msg: types.Message):
    is_subscribed = await check_subscription(msg.from_user.id)
    if not is_subscribed:
        await msg.answer("🔒 Подпишись на канал!")
        return
    
    async with aiosqlite.connect(db_path) as db:
        cursor = await db.execute("SELECT id, name, price, stock FROM games WHERE stock > 0")
        games = await cursor.fetchall()
    
    text = "📦 **Каталог:**\n\n"
    kb = types.InlineKeyboardMarkup(inline_keyboard=[])
    for game in games:
        text += f"🎮 {game[1]} — {game[2]}₽\n"
        kb.inline_keyboard.append([types.InlineKeyboardButton(text=f"Купить", callback_data=f"buy_{game[0]}")])
    
    await msg.answer(text, reply_markup=kb, parse_mode="Markdown")

@dp.callback_query(F.data.startswith("buy_"))
async def buy_game(callback: types.CallbackQuery, state: FSMContext):
    game_id = int(callback.data.split("_")[1])
    async with aiosqlite.connect(db_path) as db:
        cursor = await db.execute("SELECT name, price, key FROM games WHERE id=?", (game_id,))
        game = await cursor.fetchone()
    
    if not game:
        await callback.answer("❌ Товара нет!")
        return
    
    await state.update_data(game_id=game_id, game_name=game[0], game_key=game[2], game_price=game[1])
    
    try:
        payment = Payment.create({
            "amount": {"value": str(game[1]), "currency": "RUB"},
            "confirmation": {"type": "redirect", "return_url": "https://t.me/"},
            "description": f"Покупка: {game[0]}"
        })
        
        kb = types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text="💳 Оплатить", url=payment.confirmation.confirmation_url)],
            [types.InlineKeyboardButton(text="✅ Я оплатил", callback_data=f"confirm_{game_id}")]
        ])
        await callback.message.answer(f"💳 {game[0]} — {game[1]}₽", reply_markup=kb)
    except Exception as e:
        await callback.answer(f"❌ Ошибка: {str(e)}")

@dp.callback_query(F.data.startswith("confirm_"))
async def confirm(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    game_id = data.get("game_id")
    game_name = data.get("game_name")
    game_key = data.get("game_key")
    
    async with aiosqlite.connect(db_path) as db:
        await db.execute("UPDATE games SET stock = stock - 1 WHERE id=?", (game_id,))
        await db.commit()
    
    await callback.message.answer(f"✅ **Спасибо!**\n\n🎮 {game_name}\n🔑 `{game_key}`", parse_mode="Markdown")
    await state.clear()

@dp.message(F.text == "ℹ️ О нас")
async def about(msg: types.Message):
    await msg.answer("ℹ️ Мы продаем лицензионные ключи Steam!")

@dp.message(F.text == "🎁 Бесплатные ключи")
async def free(msg: types.Message):
    await msg.answer("🎁 FREE-KEY-001\n🎁 FREE-KEY-002")

@dp.message(F.text == "🔥 Акции")
async def sales(msg: types.Message):
    await msg.answer("🔥 **Скидки сегодня:**\nCyberpunk -20%")

async def main():
    await init_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
