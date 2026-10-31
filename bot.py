import asyncio
import logging
import os
import re
import secrets
from dataclasses import dataclass
from typing import Dict

from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandStart
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)

# Set BOT_TOKEN as an environment variable. Do not paste your token into this file.
BOT_TOKEN = "9252419350:AAGu-FIGtA1irndOvzg_5lfWQypQiVVCcyk"
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN не указан")

logging.basicConfig(level=logging.INFO)

bot = Bot(
    BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML),
)
dp = Dispatcher()

GIFT_RE = re.compile(r"^https?://t\.me/nft/([A-Za-z]+)-(\d+)/?$")

# Premium emoji IDs supplied in the user's previous code.
E_GEM = "5318901904686754959"
E_OK = "5774022692642492953"
E_NO = "5774077015388852135"
E_TIMER = "6037268453759389862"
E_GIFT = "5773677501825945508"
E_STAR = "6028338546736107668"

@dataclass
class DemoOffer:
    owner_id: int
    gift_url: str
    gift_name: str
    gift_number: str
    amount: float
    currency: str
    status: str = "pending"

offers: Dict[str, DemoOffer] = {}


def em(emoji_id: str, fallback: str) -> str:
    return f'<tg-emoji emoji-id="{emoji_id}">{fallback}</tg-emoji>'


def amount_text(amount: float, currency: str) -> str:
    if currency == "GRAM":
        return f'{em(E_GEM, "💎")} <b>{amount:g} GRAM</b>'
    return f'{em(E_STAR, "⭐")} <b>{amount:g} STARS</b>'


def offer_keyboard(offer_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(
            text="Отклонить",
            callback_data=f"demo:decline:{offer_id}",
            icon_custom_emoji_id=E_NO,
        ),
        InlineKeyboardButton(
            text="Принять (тест)",
            callback_data=f"demo:accept:{offer_id}",
            icon_custom_emoji_id=E_OK,
        ),
    ]])


def offer_text(offer_id: str, offer: DemoOffer) -> str:
    return (
        f'{em(E_GIFT, "🎁")} <b>ТЕСТОВЫЙ NFT-ОФФЕР</b>\n\n'
        f'Подарок: <a href="{offer.gift_url}">'
        f'{offer.gift_name} #{offer.gift_number}</a>\n'
        f'Цена: {amount_text(offer.amount, offer.currency)}\n'
        f'{em(E_TIMER, "⏱")} Статус: ожидает ответа\n\n'
        f'<i>Демонстрация: принятие не переводит NFT или деньги.</i>\n'
        f'<code>Тестовый ID: {offer_id}</code>'
    )


@dp.message(CommandStart())
async def start(message: Message):
    await message.answer(
        "Привет! Это демонстрационный бот для тестирования NFT-офферов.\n\n"
