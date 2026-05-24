from typing import Any, Awaitable, Callable, Dict
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Update, Message, CallbackQuery
from database.db import Database

class DbMiddleware(BaseMiddleware):
    def __init__(self, db: Database):
        super().__init__()
        self.db = db

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        user = None

        # dp.update.outer_middleware da event — Update ob'ekti bo'ladi (aiogram 3.4+).
        # Shuning uchun ichki eventdan (message, callback_query, ...) user ni olamiz.
        if isinstance(event, Update):
            inner = event.message or event.callback_query or event.edited_message or event.inline_query
            if inner and hasattr(inner, "from_user") and inner.from_user:
                user = inner.from_user
        elif isinstance(event, (Message, CallbackQuery)) and event.from_user:
            # Agar middleware message/callback_query darajasida ro'yxatdan o'tgan bo'lsa
            user = event.from_user

        # Har doim db ni inject qilamiz (user bo'lmasa ham, ba'zi handlerlar faqat db kerak)
        data["db"] = self.db

        if user and not user.is_bot:
            # Foydalanuvchini ro'yxatdan o'tkazish / ma'lumotlarini yangilash
            await self.db.add_user(
                user_id=user.id,
                username=user.username,
                first_name=user.first_name,
                last_name=user.last_name or ""
            )
            # Handler larga user sozlamalarini uzatish
            settings = await self.db.get_user_settings(user.id)
            data["user_settings"] = settings
        else:
            # Default sozlamalar (user topilmasa)
            data.setdefault("user_settings", {
                "pdf_quality": "medium",
                "watermark_text": None,
                "is_admin": False
            })

        return await handler(event, data)
