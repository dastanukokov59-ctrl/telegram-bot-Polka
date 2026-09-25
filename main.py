import os
import asyncio
import logging
from aiohttp import web, ClientSession
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile
from aiogram.enums import ParseMode

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Получение переменных окружения
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN") or os.environ.get("BOT_TOKEN")
TELEGRAM_CHANNEL_ID = os.environ.get("TELEGRAM_CHANNEL_ID") or "@hatapolskoi"
TWITCH_CLIENT_ID = os.environ.get("TWITCH_CLIENT_ID")
TWITCH_CLIENT_SECRET = os.environ.get("TWITCH_CLIENT_SECRET")
TWITCH_CHANNEL_NAME = os.environ.get("TWITCH_CHANNEL_NAME") or "po1ka_1839"

IMAGE_FILE_PATH = "cat.jpg"

bot = Bot(token=TELEGRAM_BOT_TOKEN)
dp = Dispatcher()

twitch_access_token = None
is_live = False


async def get_twitch_access_token():
    global twitch_access_token
    url = "https://id.twitch.tv/oauth2/token"
    params = {
        "client_id": TWITCH_CLIENT_ID,
        "client_secret": TWITCH_CLIENT_SECRET,
        "grant_type": "client_credentials"
    }
    async with ClientSession() as session:
        async with session.post(url, params=params) as resp:
            data = await resp.json()
            twitch_access_token = data.get("access_token")


async def get_stream_info():
    global twitch_access_token
    if not twitch_access_token:
        await get_twitch_access_token()

    url = f"https://api.twitch.tv/helix/streams?user_login={TWITCH_CHANNEL_NAME}"
    headers = {
        "Client-ID": TWITCH_CLIENT_ID,
        "Authorization": f"Bearer {twitch_access_token}"
    }

    async with ClientSession() as session:
        async with session.get(url, headers=headers) as resp:
            if resp.status == 401:
                await get_twitch_access_token()
                headers["Authorization"] = f"Bearer {twitch_access_token}"
                async with session.get(url, headers=headers) as resp_retry:
                    data = await resp_retry.json()
            else:
                data = await resp.json()

            streams = data.get("data", [])
            if streams:
                return streams[0]
            return None


async def send_stream_start_notification(stream_info):
    title = stream_info.get("title", "")
    game_name = stream_info.get("game_name", "")

    caption_text = (
        f"<b>КОШКА ОТКРЫЛА КАФЕ! 🐾</b>\n\n"
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
        if os.path.exists(IMAGE_FILE_PATH):
            photo = FSInputFile(IMAGE_FILE_PATH)
            await bot.send_photo(
                chat_id=TELEGRAM_CHANNEL_ID,
                photo=photo,
                caption=caption_text,
                parse_mode=ParseMode.HTML,
                reply_markup=keyboard
            )
        else:
            await bot.send_message(
                chat_id=TELEGRAM_CHANNEL_ID,
                text=caption_text,
                parse_mode=ParseMode.HTML,
                reply_markup=keyboard
            )
    except Exception as e:
        logging.error(f"Ошибка отправки сообщения о начале стрима: {e}")


async def send_stream_end_notification():
    text = "Кошка закончила смену 🐾\nСпасибо всем за стрим!"
    try:
        await bot.send_message(chat_id=TELEGRAM_CHANNEL_ID, text=text)
    except Exception as e:
        logging.error(f"Ошибка отправки сообщения об окончании стрима: {e}")

async def check_stream_loop():
    global is_live
    while True:
        try:
            stream_info = await get_stream_info()
            if stream_info:
                if not is_live:
                    is_live = True
                    await send_stream_start_notification(stream_info)
            else:
                if is_live:
                    is_live = False
                    await send_stream_end_notification()
        except Exception as e:
            logging.error(f"Ошибка в цикле проверки: {e}")

        await asyncio.sleep(60)


# Веб-сервер для Render (чтобы сервис не уходил в сон)
async def handle(request):
    return web.Response(text="Bot is running!")


async def start_dummy_server():
    app = web.Application()
    app.router.add_get("/", handle)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()


async def main():
    # Запускаем фоновый веб-сервер для Render
    await start_dummy_server()

    # Запускаем проверку стрима в фоновом режиме
    asyncio.create_task(check_stream_loop())

    # Запуск бота
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
