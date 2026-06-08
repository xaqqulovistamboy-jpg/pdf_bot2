from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

def get_main_keyboard() -> InlineKeyboardMarkup:
    """Yangi boshlash yoki asosiy menyu inline klaviaturasi"""
    builder = InlineKeyboardBuilder()
    
    # Tugmalarni qo'shish
    builder.row(
        InlineKeyboardButton(text="📤 Rasm yuborish", callback_data="how_to_send")
    )
    builder.row(
        InlineKeyboardButton(text="📄 PDF yaratish", callback_data="create_pdf"),
        InlineKeyboardButton(text="❌ Bekor qilish", callback_data="cancel_process")
    )
    builder.row(
        InlineKeyboardButton(text="ℹ️ Yordam", callback_data="help_info"),
        InlineKeyboardButton(text="⚙️ Sozlamalar", callback_data="settings_menu")
    )
    builder.row(
        InlineKeyboardButton(text="📊 Statistika", callback_data="show_stats")
    )
    
    return builder.as_markup()

def get_stats_keyboard() -> InlineKeyboardMarkup:
    """Statistika oynasi uchun inline klaviatura (faqat orqaga tugmasi)"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🔙 Orqaga", callback_data="main_menu")
    )
    return builder.as_markup()

def get_settings_keyboard(quality: str, watermark_text: str) -> InlineKeyboardMarkup:
    """Sozlamalar klaviaturasi: sifat va watermark sozlamalarini o'zgartirish"""
    builder = InlineKeyboardBuilder()
    
    # Sifat tugmalari (Low, Medium, High)
    q_low = "✅ Pas 📉" if quality == "low" else "Pas 📉"
    q_med = "✅ O'rta 📊" if quality == "medium" else "O'rta 📊"
    q_high = "✅ Yuqori 📈" if quality == "high" else "Yuqori 📈"
    
    builder.row(
        InlineKeyboardButton(text=q_low, callback_data="set_quality_low"),
        InlineKeyboardButton(text=q_med, callback_data="set_quality_medium"),
        InlineKeyboardButton(text=q_high, callback_data="set_quality_high")
    )
    
    # Watermark tugmasi
    wm_status = f"✅ Watermark: '{watermark_text}'" if watermark_text else "❌ Watermark o'chirilgan"
    builder.row(
        InlineKeyboardButton(text=wm_status, callback_data="toggle_watermark")
    )
    
    # Orqaga qaytish
    builder.row(
        InlineKeyboardButton(text="🔙 Orqaga", callback_data="main_menu")
    )
    
    return builder.as_markup()

def get_admin_keyboard() -> InlineKeyboardMarkup:
    """Admin panel uchun klaviatura"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="📊 Statistika", callback_data="admin_stats"),
        InlineKeyboardButton(text="📣 Reklama Tarqatish", callback_data="admin_broadcast")
    )
    builder.row(
        InlineKeyboardButton(text="👥 Foydalanuvchilar soni", callback_data="admin_users_count")
    )
    builder.row(
        InlineKeyboardButton(text="❌ Yopish", callback_data="admin_close")
    )
    return builder.as_markup()

def get_pdf_creation_keyboard() -> InlineKeyboardMarkup:
    """Rasmlar yuborilgandan keyin ko'rsatiladigan klaviatura"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="📄 PDF ni yaratish", callback_data="create_pdf"),
        InlineKeyboardButton(text="❌ Bekor qilish", callback_data="cancel_process")
    )
    return builder.as_markup()
