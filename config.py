import os
from dotenv import load_dotenv

# .env fayldan o'zgaruvchilarni o'qish
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    raise ValueError("Diqqat! .env faylida BOT_TOKEN ko'rsatilmagan.")
