import asyncio
import logging
import sys
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from config import BOT_TOKEN
from database.db import Database
from middlewares.db_middleware import DbMiddleware
from middlewares.rate_limit import RateLimitMiddleware
from handlers import commands, images, pdf_operations, admin

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

async def on_startup(bot: Bot, db: Database):
    # Initialize the database tables
    logger.info("Initializing SQLite database...")
    await db.init_db()
    logger.info("Database initialized successfully.")

async def main():
    # Create Database instance
    db = Database()
    
    # Bot object with HTML/Markdown properties
    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    
    # Dispatcher object
    dp = Dispatcher()
    
    # Register global middlewares
    # Outer middleware runs on all updates (message, callback query, etc.)
    dp.update.outer_middleware(DbMiddleware(db))
    # Message-specific rate limiting middleware
    dp.message.middleware(RateLimitMiddleware(limit=0.8))
    
    # Include all routers
    # Make sure admin router is matched before others to prevent conflict
    dp.include_router(admin.router)
    dp.include_router(commands.router)
    dp.include_router(pdf_operations.router)
    dp.include_router(images.router)
    
    # Startup tasks
    await on_startup(bot, db)
    
    logger.info("Starting Telegram Bot polling...")
    
    # Skip updates that arrived while bot was offline
    await bot.delete_webhook(drop_pending_updates=True)
    
    # Start polling
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped successfully.")
