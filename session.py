from telethon.sync import TelegramClient

API_ID   = 34624108
API_HASH = "e8095d777dea9b5066a130eab3f7aa67"

with TelegramClient("userbot_session", API_ID, API_HASH) as client:
    print("Сессия создана:", client.get_me().username)