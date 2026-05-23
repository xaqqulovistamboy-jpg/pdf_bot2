import time
from typing import Any, Awaitable, Callable, Dict
from aiogram import BaseMiddleware
from aiogram.types import Message

class RateLimitMiddleware(BaseMiddleware):
    def __init__(self, limit: float = 0.8):
        """
        limit: seconds between messages.
        """
        self.limit = limit
        self.last_timestamps: Dict[int, float] = {}

    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: Dict[str, Any]
    ) -> Any:
        # Ignore non-message events if middleware is registered on other handlers
        if not isinstance(event, Message) or not event.from_user:
            return await handler(event, data)

        user_id = event.from_user.id
        current_time = time.time()

        # If it's part of a media group, bypass the rate limiter
        # so multiple images in a single send are not blocked
        if event.media_group_id:
            return await handler(event, data)

        last_time = self.last_timestamps.get(user_id, 0.0)
        if current_time - last_time < self.limit:
            # Silently ignore or alert the user
            # To keep user experience clean, we can ignore or reply once.
            # Let's reply only if they haven't been warned in the last 3 seconds
            last_warning = data.get(f"warn_{user_id}", 0.0)
            if current_time - last_warning > 3.0:
                data[f"warn_{user_id}"] = current_time
                await event.answer("⚠️ Iltimos, xabarlarni juda tez-tez yubormang!")
            return

        self.last_timestamps[user_id] = current_time
        return await handler(event, data)
