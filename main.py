python
import asyncio
import logging
import os
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import PreCheckoutQuery, FSInputFile
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
import aiosqlite
import aiofiles
from yookassa import Configuration, Payment

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
YOOKASSA_SHOP_ID = os.getenv("YOOKASSA_SHOP_ID")
YOOKASSA_SECRET = os.getenv("YOOKASSA_SECRET")
ADMIN_ID = int(os.getenv("ADMIN_ID", 0))

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
        await db.execute("INSERT OR IGNORE INTO games (name, description, price, photo_path, stock, key) VALUES (?, ?, ?, ?, ?, ?)",
                         ("GTA V", "Открытый мир, экшн. Steam ключ.", 500, "images/gta.jpg", 10, "GTA5-ABC123-DEF"))
        await db.commit()

@dp.message(CommandStart())
async def start(msg: types.Message):
    kb = types.ReplyKeyboardMarkup(keyboard=[[types.KeyboardButton(text="📦 Каталог")]])
    await msg.answer("🎮 Добро пожаловать в магазин ключей игр!\nВыберите действие:", reply_markup=kb)

@dp.message(F.text == "📦 Каталог")
async def show_catalog(msg: types.Message):
    async with aiosqlite.connect(db_path) as db:
        cursor = await db.execute("SELECT id, name, price, stock FROM games WHERE stock > 0")
        games = await cursor.fetchall()
    if not games:
        await msg.answer("❌ Каталог пуст или товары закончились.")
        return
    text = "📦 **Каталог игр:**\n\n"
    kb_inline = types.InlineKeyboardMarkup(inline_keyboard=[])
    for game in games:
        text += f"🎮 **{game[1]}** — {game[2]}₽ (в наличии: {game[3]})\n"
        kb_inline.inline_keyboard.append([types.InlineKeyboardButton(text=f"Купить {game[1]}", callback_data=f"buy_{game[0]}")])
    await msg.answer(text, reply_markup=kb_inline, parse_mode="Markdown")

@dp.callback_query(F.data.startswith("buy_"))
async def process_buy(callback: types.CallbackQuery, state: FSMContext):
    game_id = int(callback.data.split("_")[1])
    async with aiosqlite.connect(db_path) as db:
        cursor = await db.execute("SELECT name, description, price, photo_path, key FROM games WHERE id=? AND stock > 0", (game_id,))
        game = await cursor.fetchone()
    if game:
        await state.update_data(game_id=game_id, key=game[4])
        try:
            photo = FSInputFile(game[3])
            await callback.message.answer_photo(
                photo=photo,
                caption=f"🎮 **{game[0]}**\n{game[1]}\n💰 **{game[2]}₽**\n\nНажмите кнопку ниже для оплаты:",
                parse_mode="Markdown"
            )
        except:
            await callback.message.answer(f"🎮 **{game[0]}**\n{game[1]}\n💰 **{game[2]}₽**")
        
        await bot.send_invoice(
            chat_id=callback.message.chat.id,
            title=game[0],
            description=game[1],
            payload=f"game_{game_id}",
            provider_token="",
            currency="RUB",
            prices=[types.LabeledPrice(label=game[0], amount=game[2] * 100)]
        )
    else:
        await callback.answer("❌ Нет в наличии!", show_alert=True)

@dp.pre_checkout_query()
async def pre_checkout(pre_checkout_q: PreCheckoutQuery):
    await bot.answer_pre_checkout_query(pre_checkout_q.id, ok=True)

@dp.message(F.successful_payment)
async def got_payment(msg: types.Message, state: FSMContext):
    data = await state.get_data()
    game_id = data['game_id']
    key = data['key']
    
    async with aiosqlite.connect(db_path) as db:
        async with db.execute("SELECT name FROM games WHERE id=?", (game_id,)) as cursor:
            game = await cursor.fetchone()
        await db.execute("UPDATE games SET stock = stock - 1 WHERE id=?", (game_id,))
        await db.commit()
    
    await msg.answer(
        f"✅ **Спасибо за покупку!**\n\n🎮 Игра: {game[0]}\n🔑 Ваш ключ:\n`{key}`\n\nСохраните ключ! Активируйте его в Steam.",
        parse_mode="Markdown"
    )
    await state.clear()

async def main():
    await init_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
