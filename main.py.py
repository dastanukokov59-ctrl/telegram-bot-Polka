import asyncio
import logging
import os
from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile
import aiohttp

# ================= НАСТРОЙКИ =================
TELEGRAM_TOKEN = "8921498714:AAFikUnB6Q0MT00eKyKIaEeaVcVb55fZMcw"
CHANNEL_ID = "@hatapolskoi"

TWITCH_CLIENT_ID = "i1azl7j4rto97dfc3f12qgx7m1snjz"
TWITCH_CLIENT_SECRET = "imn4jz2e04arzsinmb1anz0fntyst5"
TWITCH_CHANNEL_NAME = "po1ka_1839"

# Имя файла с котиком, который лежит в той же папке
IMAGE_FILE_PATH = "cat.jpg" 
# Запасная ссылка на случай, если файла нет
DEFAULT_IMAGE_URL = "https://placehold.co/1280x720/png?text=Stream+Online" 
# =============================================

logging.basicConfig(level=logging.INFO)
bot = Bot(token=TELEGRAM_TOKEN)

twitch_access_token = None
is_live = False

async def get_twitch_access_token():
    """Получение доступа к Twitch API"""
    global twitch_access_token
    url = "https://id.twitch.tv/oauth2/token"
    params = {
        "client_id": TWITCH_CLIENT_ID,
        "client_secret": TWITCH_CLIENT_SECRET,
        "grant_type": "client_credentials"
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(url, params=params) as resp:
            data = await resp.json()
            twitch_access_token = data.get("access_token")

async def check_stream_status():
    """Проверка статуса стрима у po1ka_1839"""
    global is_live, twitch_access_token
    
    if not twitch_access_token:
        await get_twitch_access_token()

    url = f"https://api.twitch.tv/helix/streams?user_login={TWITCH_CHANNEL_NAME}"
    headers = {
        "Client-ID": TWITCH_CLIENT_ID,
        "Authorization": f"Bearer {twitch_access_token}"
    }

    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as resp:
            if resp.status == 401:
                await get_twitch_access_token()
                return
            
            data = await resp.json()
            streams = data.get("data", [])

            if streams:
                stream_info = streams[0]
                if not is_live:
                    is_live = True
                    await send_stream_start_notification(stream_info)
            else:
                if is_live:
                    is_live = False
                    await send_stream_end_notification()

async def send_stream_start_notification(stream_info):
    """Анонс в @hatapolskoi о начале стрима"""
    title = stream_info.get("title", "")
    game_name = stream_info.get("game_name", "")

    caption_text = (
        f"<b>Кошка открыла кафе! 🐾</b>\n\n"
        f"<b>{title}</b>\n"
        f"🎮 <b>Категория:</b> {game_name}"
    )

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🐾 Зайти в кафе", 
                    url=f"https://www.twitch.tv/{TWITCH_CHANNEL_NAME}"
                )
            ]
        ]
    )

    try:
        # Проверяем, есть ли локальная картинка с котиком
        if os.path.exists(IMAGE_FILE_PATH):
            photo = FSInputFile(IMAGE_FILE_PATH)
        else:
            # Если файла cat.jpg нет, берем превью с Twitch
            photo = stream_info.get("thumbnail_url", "").replace("{width}", "1280").replace("{height}", "720")
            if not photo:
                photo = DEFAULT_IMAGE_URL

        await bot.send_photo(
            chat_id=CHANNEL_ID,
            photo=photo,
            caption=caption_text,
            parse_mode="HTML",
            reply_markup=keyboard
        )
        logging.info("Уведомление о начале стрима отправлено!")
    except Exception as e:
        logging.error(f"Ошибка при отправке анонса: {e}")

async def send_stream_end_notification():
    """Сообщение в @hatapolskoi о завершении стрима"""
    end_text = "<b>Кошка закончила смену 🐾</b>\n\nСпасибо всем за стрим!"
    
    try:
        await bot.send_message(
            chat_id=CHANNEL_ID,
            text=end_text,
            parse_mode="HTML"
        )
        logging.info("Уведомление о завершении отправлено!")
    except Exception as e:
        logging.error(f"Ошибка отправки сообщения о завершении: {e}")

async def main():
    print("Бот запущен и отслеживает Twitch-канал po1ka_1839...")
    while True:
        try:
            await check_stream_status()
        except Exception as e:
            logging.error(f"Ошибка проверки стрима: {e}")
        
        await asyncio.sleep(60)

if __name__ == "__main__":
    asyncio.run(main())