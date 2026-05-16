import asyncio
import logging
from aiogram import Bot, Dispatcher
from config import BOT_TOKEN
from handlers import commands, images

# Loggingni sozlash (terminalda qulay ko'rish uchun)
logging.basicConfig(level=logging.INFO)

async def main():
    # Bot obyektini yaratish
    bot = Bot(token=BOT_TOKEN)
    
    # Dispatcher obyektini yaratish
    dp = Dispatcher()
    
    # Yaratilgan routerlarni ulab chiqish
    dp.include_router(commands.router)
    dp.include_router(images.router)
    
    print("🚀 Bot muvaffaqiyatli ishga tushdi...")
    
    # Eski (bot o'chganda kelgan) xabarlarni e'tiborsiz qoldirish
    await bot.delete_webhook(drop_pending_updates=True)
    # Polling orqali botni ishga tushirish
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("🛑 Bot to'xtatildi!")
