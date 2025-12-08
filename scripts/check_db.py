#!/usr/bin/env python3
import os
import asyncio

from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, Router
from aiogram.filters import Command
from aiogram.types import Message

# --- отладка загрузки .env ---
print("CWD:", os.getcwd())
print("ENV BEFORE load_dotenv: TELEGRAM_BOT_TOKEN =", os.getenv("TELEGRAM_BOT_TOKEN"))

# грузим .env из текущей папки
load_dotenv()

print("ENV AFTER load_dotenv: TELEGRAM_BOT_TOKEN =", os.getenv("TELEGRAM_BOT_TOKEN"))
# --- конец отладки ---

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

if not TELEGRAM_BOT_TOKEN:
    raise RuntimeError("TELEGRAM_BOT_TOKEN не найден даже после load_dotenv()")

bot = Bot(token=TELEGRAM_BOT_TOKEN)
dp = Dispatcher()
router = Router()
dp.include_router(router)


@router.message(Command("start"))
async def cmd_start(message: Message):
    await message.answer(
        "Добро пожаловать в систему определения пригодности дел для судебного приказа!\n" \
        ""
    )


async def main():
    print("Telegram bot started. Waiting for updates...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
