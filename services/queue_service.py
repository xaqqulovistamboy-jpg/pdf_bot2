import os
import asyncio
from typing import Dict, List, Callable, Optional, Any
from aiogram.types import Message

class UserSession:
    def __init__(self, user_id: int):
        self.user_id = user_id
        # List of dicts: {"path": str, "message_id": int}
        self.images: List[Dict[str, Any]] = []
        # List of dicts: {"path": str, "message_id": int}
        self.pdfs: List[Dict[str, Any]] = []
        
        self.timer_task: Optional[asyncio.Task] = None
        self.summary_message: Optional[Message] = None
        self.lock = asyncio.Lock()

    def get_sorted_images(self) -> List[str]:
        """Sorts collected images strictly by message_id to preserve sent order"""
        sorted_items = sorted(self.images, key=lambda x: x["message_id"])
        return [item["path"] for item in sorted_items]

    def get_sorted_pdfs(self) -> List[str]:
        """Sorts collected PDFs strictly by message_id"""
        sorted_items = sorted(self.pdfs, key=lambda x: x["message_id"])
        return [item["path"] for item in sorted_items]

    async def cancel_timer(self):
        if self.timer_task and not self.timer_task.done():
            self.timer_task.cancel()
            try:
                await self.timer_task
            except asyncio.CancelledError:
                pass
            self.timer_task = None

    def clean_files(self):
        """Removes all files associated with this session from the disk"""
        for img in self.images:
            path = img["path"]
            if os.path.exists(path):
                try:
                    os.remove(path)
                except OSError:
                    pass
        for pdf in self.pdfs:
            path = pdf["path"]
            if os.path.exists(path):
                try:
                    os.remove(path)
                except OSError:
                    pass
        self.images.clear()
        self.pdfs.clear()


class QueueManager:
    def __init__(self, debounce_seconds: float = 1.2):
        self.sessions: Dict[int, UserSession] = {}
        self.debounce_seconds = debounce_seconds

    def get_session(self, user_id: int) -> UserSession:
        if user_id not in self.sessions:
            self.sessions[user_id] = UserSession(user_id)
        return self.sessions[user_id]

    async def add_image(
        self, 
        user_id: int, 
        file_path: str, 
        message_id: int, 
        trigger_message: Message,
        callback: Callable[[UserSession, Message], Any]
    ):
        """Adds an image path to user's session and debounces the callback trigger"""
        session = self.get_session(user_id)
        
        async with session.lock:
            session.images.append({"path": file_path, "message_id": message_id})
            await session.cancel_timer()
            
            # Create a debounced task
            async def _debounce_wait():
                try:
                    await asyncio.sleep(self.debounce_seconds)
                    # Trigger callback once quiet
                    await callback(session, trigger_message)
                except asyncio.CancelledError:
                    pass
                
            session.timer_task = asyncio.create_task(_debounce_wait())

    async def add_pdf(
        self, 
        user_id: int, 
        file_path: str, 
        message_id: int, 
        trigger_message: Message,
        callback: Callable[[UserSession, Message], Any]
    ):
        """Adds a PDF path to user's session and debounces the callback trigger"""
        session = self.get_session(user_id)
        
        async with session.lock:
            session.pdfs.append({"path": file_path, "message_id": message_id})
            await session.cancel_timer()
            
            async def _debounce_wait():
                try:
                    await asyncio.sleep(self.debounce_seconds)
                    await callback(session, trigger_message)
                except asyncio.CancelledError:
                    pass
                
            session.timer_task = asyncio.create_task(_debounce_wait())

    async def clear_session(self, user_id: int):
        """Fully resets and cleans up a user's session"""
        if user_id in self.sessions:
            session = self.sessions[user_id]
            await session.cancel_timer()
            session.clean_files()
            del self.sessions[user_id]
