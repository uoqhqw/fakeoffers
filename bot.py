        "Создать тестовый оффер:\n"
        "<code>/offer https://t.me/nft/BerryBox-40761 15000 STARS</code>\n"
        "или\n"
        "<code>/offer https://t.me/nft/DurovsCap-3340 33 GRAM</code>\n\n"
        "Офферы помечаются как тестовые и не выполняют реальные переводы."
    )


@dp.message(Command("offer"))
async def create_offer(message: Message):
    parts = (message.text or "").split()
    if len(parts) != 4:
        await message.answer(
            "Формат:\n"
            "<code>/offer https://t.me/nft/BerryBox-40761 15000 STARS</code>"
        )
        return

    _, gift_url, amount_raw, currency_raw = parts
    match = GIFT_RE.fullmatch(gift_url)
    if not match:
        await message.answer("Не удалось распознать NFT-ссылку. Проверь формат t.me/nft/Name-123.")
        return

    try:
        amount = float(amount_raw.replace(",", "."))
        if amount <= 0:
            raise ValueError
    except ValueError:
        await message.answer("Цена должна быть положительным числом.")
        return

    currency = currency_raw.upper()
    if currency not in {"STARS", "GRAM"}:
        await message.answer("Валюта должна быть STARS или GRAM.")
        return

    gift_name, gift_number = match.groups()
    offer_id = secrets.token_hex(4).upper()
    offer = DemoOffer(
        owner_id=message.from_user.id,
        gift_url=gift_url,
        gift_name=gift_name,
        gift_number=gift_number,
        amount=amount,
        currency=currency,
    )
    offers[offer_id] = offer

    await message.answer(
        offer_text(offer_id, offer),
        reply_markup=offer_keyboard(offer_id),
        disable_web_page_preview=False,
    )


@dp.callback_query(F.data.startswith("demo:"))
async def handle_demo_action(callback: CallbackQuery):
    try:
        _, action, offer_id = callback.data.split(":")
    except (AttributeError, ValueError):
        await callback.answer("Некорректная кнопка.", show_alert=True)
        return

    offer = offers.get(offer_id)
    if offer is None:
        await callback.answer("Тестовый оффер не найден или бот перезапускался.", show_alert=True)
        return

    if callback.from_user.id != offer.owner_id:
        await callback.answer(
            "В этой демонстрационной версии менять статус может только создатель оффера.",
            show_alert=True,
        )
        return

    if offer.status != "pending":
        await callback.answer("Этот тестовый оффер уже обработан.", show_alert=True)
        return

    if action == "accept":
        offer.status = "accepted_demo"
        status_text = f'{em(E_OK, "✅")} <b>ТЕСТОВЫЙ ОФФЕР ПРИНЯТ</b>'
    elif action == "decline":
        offer.status = "declined_demo"
        status_text = f'{em(E_NO, "❌")} <b>ТЕСТОВЫЙ ОФФЕР ОТКЛОНЁН</b>'
    else:
        await callback.answer("Неизвестное действие.", show_alert=True)
        return

    await callback.message.edit_text(
        offer_text(offer_id, offer).replace(
            "Статус: ожидает ответа",
            f"Статус: {offer.status}",
        ) + "\n\n" + status_text,
        reply_markup=None,
        disable_web_page_preview=False,
    )
    await callback.answer("Статус тестового оффера обновлён.")


async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
