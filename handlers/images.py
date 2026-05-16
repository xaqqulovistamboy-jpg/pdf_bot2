import os
import uuid
from datetime import datetime
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.types import FSInputFile
from utils.pdf import create_pdf_from_images

router = Router()

# Foydalanuvchilarning rasmlarini saqlash uchun lug'at (in-memory storage)
# Format: { user_id: ["path1.jpg", "path2.jpg", ...] }
user_images = {}

# Vaqtinchalik fayllarni saqlash papkasi
TEMP_DIR = "temp"
os.makedirs(TEMP_DIR, exist_ok=True)

def get_pdf_keyboard():
    """PDF yaratish uchun inline klaviatura"""
    keyboard = [
        [InlineKeyboardButton(text="📄 PDF ni yaratish", callback_data="create_pdf")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

@router.message(F.photo | F.document)
async def handle_image(message: Message):
    user_id = message.from_user.id
    
    # Agar fayl ko'rinishida jo'natilsa, rasm ekanligini tekshiramiz
    if message.document and not message.document.mime_type.startswith('image/'):
        await message.answer("❌ Iltimos, faqat rasm formatidagi fayllarni yuboring.")
        return

    # Foydalanuvchi ma'lumotlarini initsializatsiya qilish
    if user_id not in user_images:
        user_images[user_id] = []

    # Fayl ID sini olish
    if message.photo:
        # Eng katta o'lchamdagi rasmni (sifatliroq) tanlaymiz
        file_id = message.photo[-1].file_id
        file_extension = "jpg"
    else:
        file_id = message.document.file_id
        file_name = message.document.file_name
        file_extension = file_name.split('.')[-1] if '.' in file_name else "jpg"

    try:
        # Faylni Telegram serverlaridan yuklab olish
        file = await message.bot.get_file(file_id)
        file_path = file.file_path
        
        # Tasodifiy unikal fayl nomi generatsiyasi
        unique_name = f"{uuid.uuid4().hex}.{file_extension}"
        local_path = os.path.join(TEMP_DIR, unique_name)
        
        await message.bot.download_file(file_path, local_path)
        user_images[user_id].append(local_path)
        
        await message.answer(
            f"✅ Rasm qabul qilindi! (Jami: {len(user_images[user_id])} ta rasm)\n"
            "Yana rasm yuborishingiz yoki pastdagi tugmani bosib PDF ni yaratishingiz mumkin.",
            reply_markup=get_pdf_keyboard()
        )
    except Exception as e:
        await message.answer(f"❌ Rasmni yuklashda xatolik yuz berdi: {e}")

@router.callback_query(F.data == "create_pdf")
async def process_create_pdf(callback: CallbackQuery):
    user_id = callback.from_user.id
    
    if user_id not in user_images or not user_images[user_id]:
        await callback.message.edit_text("❌ Hech qanday rasm topilmadi. Iltimos, avval rasm yuboring.")
        return
        
    await callback.message.edit_text("⏳ PDF tayyorlanmoqda, iltimos kuting...")
    
    images = user_images[user_id]
    
    # PDF fayli uchun vaqt bilan bog'liq unikal nom
    date_str = datetime.now().strftime("%Y-%m-%d_%H-%M")
    pdf_filename = os.path.join(TEMP_DIR, f"Hujjat_{date_str}_{user_id}.pdf")
    
    # Rasmlardan PDF yasash mantiqini chaqiramiz
    result_pdf = await create_pdf_from_images(images, pdf_filename)
    
    if result_pdf and os.path.exists(result_pdf):
        pdf_document = FSInputFile(result_pdf)
        try:
            await callback.message.answer_document(
                document=pdf_document,
                caption="🎉 PDF faylingiz tayyor!"
            )
            # Muvaqqat xabarni o'chirib tashlaymiz
            await callback.message.delete()
        except Exception as e:
            await callback.message.answer(f"❌ PDF yuborishda xatolik: {e}")
            
        # Fayllarni tozalash jarayoni (Clean up)
        for img_path in images:
            try:
                if os.path.exists(img_path):
                    os.remove(img_path)
            except OSError:
                pass
        try:
            if os.path.exists(result_pdf):
                os.remove(result_pdf)
        except OSError:
            pass
            
        # Ro'yxatni bo'shatish
        user_images[user_id] = []
    else:
        await callback.message.answer("❌ PDF yaratishda kutilmagan xatolik yuz berdi.")
        
    await callback.answer()
