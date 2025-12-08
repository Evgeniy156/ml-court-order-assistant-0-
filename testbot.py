import asyncio
from aiogram import Bot, Dispatcher, Router
from aiogram.filters import Command
from aiogram.types import Message

TOKEN = "7919252620:AAH7dJ2IWMqsq2SsgUxtbL5CYswZw2RzI98"

bot = Bot(token=TOKEN)
dp = Dispatcher()
router = Router()
dp.include_router(router)

@router.message(Command("start"))
async def cmd_start(message: Message):
    await message.answer("Привет!  Бот работает!")

async def main():
    print("Bot starting...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())