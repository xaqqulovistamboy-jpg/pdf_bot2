# Telegram PDF Bot 📄🤖

Production-ready Telegram bot yaratilgan bo'lib, u foydalanuvchilar yuborgan rasmlarni PDF formatiga tezkor va tartibli ravishda o'tkazib beradi. Shuningdek, botda sifatni boshqarish, watermark qo'shish, PDF-larni birlashtirish/ajratish va arxivlar bilan ishlash kabi kengaytirilgan imkoniyatlar mavjud.

## Asosiy Imkoniyatlar

1. **Rasmlarni PDF-ga o'tkazish (Images to PDF)**:
   - Yuborilgan rasmlar (photo yoki file ko'rinishida) navbat (queue) tizimi orqali `message_id` bo'yicha saralanadi. Sahifalar tartibi mutlaqo buzilmaydi.
   - Debounce texnologiyasi yordamida bot foydalanuvchini har bir rasm uchun alohida tasdiq xabari bilan charchatmaydi, balki umumiy bitta oyna ko'rsatadi.

2. **Sifatni Tanlash (Quality Options)**:
   - **Yuqori (High)**: Original rasm o'lchamlari va minimal siqish (quality=95).
   - **O'rta (Medium)**: Max o'lchami 1600px gacha qisqartiriladi va o'rtacha siqish (quality=75).
   - **Past (Low)**: Max o'lchami 1000px gacha siqiladi (quality=55), mobil internetda tezkor yuklash uchun qulay.

3. **Watermark Qo'shish**:
   - Har bir sahifaning pastki o'ng burchagida foydalanuvchi belgilagan matn semi-transparent (yarim shaffof) ko'rinishda joylashtiriladi.

4. **PDF Split & Merge**:
   - `/merge` buyrug'i yordamida bir nechta PDF-larni yagona PDF faylga birlashtirish mumkin.
   - `/split` buyrug'i orqali PDF fayl yuklanadi va u sahifalarga ajratilib, ZIP formatda foydalanuvchiga taqdim etiladi.

5. **ZIP Support**:
   - Ichida rasmlar bo'lgan `.zip` arxivini to'g'ridan-to'g'ri botga yuborish imkoni. Bot avtomatik rasmlarni ajratib olib, PDF yaratadi.

6. **Admin Panel**:
   - `/admin` buyrug'i orqali faqat belgilangan adminlar foydalana oladigan panel.
   - Oylik faol foydalanuvchilar soni (MAU), jami foydalanuvchilar, jami PDF yaratishlar soni va qayta ishlangan rasmlar soni ko'rsatiladi.
   - Foydalanuvchilarga reklama yoki xabar yuborish (Broadcasting) tizimi.

---

## Loyiha Strukturasi

```text
├── database/            # SQLite ma'lumotlar bazasi va yordamchi modullar
│   ├── db.py            # Async SQLite Database klassi
│   └── pdf_bot.db       # Ma'lumotlar bazasi fayli (avtomatik yaratiladi)
├── handlers/            # Buyruqlar va xabarlarni qayta ishlovchi modullar
│   ├── admin.py         # Admin panel va broadcasting
│   ├── commands.py      # /start, /help, /settings va tugma callbacklari
│   ├── images.py        # Rasmlar, arxivlar va PDF yaratish nomi
│   └── pdf_operations.py# /split va /merge buyruqlari
├── keyboards/           # Tugmalar (Inline va Reply)
│   └── keyboards.py     # Menyu va sozlamalar klaviaturalari
├── middlewares/         # aiogram 3 middleware-lari
│   ├── db_middleware.py # Userlarni bazada saqlash va session boshqaruvi
│   └── rate_limit.py    # Flood protection (spam cheklovi)
├── services/            # Yordamchi tashqi xizmatlar
│   ├── pdf_service.py   # PDF yaratish, sifat o'zgartirish, split/merge va ZIP
│   └── queue_service.py # Debounce navbat tizimi va fayllar saralanishi
├── states/              # FSM (State) klasslari
│   └── states.py        # Foydalanuvchi holatlari
├── temp/                # Vaqtinchalik fayllar uchun papka (avto-tozalanadi)
├── logs/                # Tizim loglari uchun papka
├── bot.py               # Loyihani ishga tushiruvchi asosiy fayl
├── config.py            # Sozlamalar va .env o'zgaruvchilari
├── Dockerfile           # Docker konfiguratsiyasi
├── docker-compose.yml   # Docker compose konfiguratsiyasi
├── requirements.txt     # Python kutubxonalari
├── Procfile             # PaaS platformalar (Render/Heroku) uchun
└── runtime.txt          # Python versiyasi
```

---

## Ishga Tushirish

### 1. Mahalliy Tizimda (Locally)

1. Loyiha papkasiga o'ting va virtual muhit yarating:
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   venv\Scripts\activate     # Windows
   ```

2. Kerakli kutubxonalarni o'rnating:
   ```bash
   pip install -r requirements.txt
   ```

3. `.env` faylini yarating va quyidagi o'zgaruvchilarni to'ldiring:
   ```env
   BOT_TOKEN=Sizning_Telegram_Bot_Tokeningiz
   ADMIN_IDS=Admin_Telegram_ID_Raqami_Vergul_Bilan_Ajratilgan
   ```

4. Botni ishga tushiring:
   ```bash
   python bot.py
   ```

### 2. Docker Yordamida

Docker yordamida botni birgina buyruq bilan ishga tushirish mumkin (ma'lumotlar bazasi va fayllar o'chib ketmaydi):

```bash
docker-compose up -d --build
```

---

## Serverga Joylashtirish (Deploy)

### 1. Render.com
1. GitHub-da yangi repository oching va loyihani unga yuklang.
2. Render.com ga kiring va **New Web Service** yoki **New Private Service** tanlang.
3. Repository-ni ulang.
4. **Environment** ni `Docker` yoki `Python` deb belgilang.
   - Agar Docker tanlansa, Render avtomatik ravishda `Dockerfile` orqali build qiladi.
   - Agar Python tanlansa, Runtime buyrug'ini `python bot.py` deb kiriting.
5. **Environment Variables** bo'limida `.env` faylidagi o'zgaruvchilarni (`BOT_TOKEN`, `ADMIN_IDS`) qo'shing.
6. Deploy tugmasini bosing.

### 2. Railway.app
1. Railway loyiha panelida **New Project** -> **Deploy from GitHub repo** tanlang.
2. Repository-ni bog'lang.
3. Loyiha sozlamalarida Variable-larni kiriting (`BOT_TOKEN`, `ADMIN_IDS`).
4. Railway avtomatik ravishda `Dockerfile` ni aniqlab botni ishga tushiradi.

### 3. VPS (Virtual Private Server)
VPS serveringizga kirgach, docker yordamida botni ishga tushirishingiz tavsiya etiladi:
```bash
git clone https://github.com/username/pdf_bot.git
cd pdf_bot
nano .env  # Token va Admin ID kiriting
docker-compose up -d --build
```

### GitHub Actions CI/CD (Auto-Deploy)
Loyiha tarkibida `.github/workflows/deploy.yml` mavjud. Siz ushbu workflow-dan foydalanib, kod main branchga push bo'lganida avtomatik Render yoki VPS serveringizga xabar berishni (Auto-deploy webhook) sozlash imkoniyatiga egasiz. GitHub repo settings-da `DEPLOY_WEBHOOK` secretini belgilasangiz kifoya.

---

## Xavfsizlik Va Sifat Kafolati

- **Spam himoyasi (Rate limit)**: Har bir foydalanuvchi uchun xabarlar o'rtasida 0.8 soniyalik cheklov qo'yilgan. Spam qiluvchilarga avtomatik ogohlantirish beriladi.
- **Xotira optimizatsiyasi (Memory cleanup)**: Foydalanuvchi PDF yaratib bo'lgandan so'ng yoki jarayonni bekor qilganda, barcha yuklangan va qayta ishlangan rasmlar va PDF fayllar diskdan avtomatik ravishda o'chiriladi.
- **Asinxron arxitektura**: Hamma uzoq davom etadigan va og'ir operatsiyalar (rasmni tahrirlash, PDF-larni birlashtirish/ajratish, ZIP ochish) alohida ThreadPoolExecutor ichida ishlaydi, bu esa botning boshqa foydalanuvchilar uchun qotib qolmasligini ta'minlaydi.
