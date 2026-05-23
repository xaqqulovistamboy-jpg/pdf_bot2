import os
import aiosqlite
from datetime import datetime, timedelta

DB_PATH = "database/pdf_bot.db"

class Database:
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        # Ensure parent directory exists
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

    async def get_connection(self):
        return await aiosqlite.connect(self.db_path)

    async def init_db(self):
        """Initialise database tables"""
        async with await self.get_connection() as db:
            # Users table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    last_name TEXT,
                    created_at TEXT NOT NULL,
                    last_active_at TEXT NOT NULL,
                    is_admin INTEGER DEFAULT 0,
                    pdf_quality TEXT DEFAULT 'medium',
                    watermark_text TEXT DEFAULT NULL
                )
            """)
            
            # Conversions table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS conversions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    file_type TEXT NOT NULL,
                    files_count INTEGER NOT NULL,
                    file_size_bytes INTEGER DEFAULT 0,
                    timestamp TEXT NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                )
            """)
            await db.commit()

    async def add_user(self, user_id: int, username: str, first_name: str, last_name: str):
        """Registers a new user or updates their profile details if already exists"""
        now = datetime.utcnow().isoformat()
        async with await self.get_connection() as db:
            await db.execute("""
                INSERT INTO users (user_id, username, first_name, last_name, created_at, last_active_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    username = excluded.username,
                    first_name = excluded.first_name,
                    last_name = excluded.last_name,
                    last_active_at = excluded.last_active_at
            """, (user_id, username, first_name, last_name, now, now))
            await db.commit()

    async def update_active(self, user_id: int):
        """Update last active timestamp for a user"""
        now = datetime.utcnow().isoformat()
        async with await self.get_connection() as db:
            await db.execute("""
                UPDATE users SET last_active_at = ? WHERE user_id = ?
            """, (now, user_id))
            await db.commit()

    async def get_user_settings(self, user_id: int) -> dict:
        """Fetch pdf_quality and watermark_text for a user"""
        async with await self.get_connection() as db:
            async with db.execute(
                "SELECT pdf_quality, watermark_text, is_admin FROM users WHERE user_id = ?", 
                (user_id,)
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    return {
                        "pdf_quality": row[0],
                        "watermark_text": row[1],
                        "is_admin": bool(row[2])
                    }
                # Default settings if user not in database yet
                return {
                    "pdf_quality": "medium",
                    "watermark_text": None,
                    "is_admin": False
                }

    async def update_user_settings(self, user_id: int, pdf_quality: str = None, watermark_text: str = None):
        """Update user preferences for quality or watermark"""
        async with await self.get_connection() as db:
            if pdf_quality is not None:
                await db.execute("UPDATE users SET pdf_quality = ? WHERE user_id = ?", (pdf_quality, user_id))
            if watermark_text is not None:
                # Store "None" string or actual value. If empty string is passed, we save as NULL
                val = None if watermark_text == "" else watermark_text
                await db.execute("UPDATE users SET watermark_text = ? WHERE user_id = ?", (val, user_id))
            await db.commit()

    async def add_conversion(self, user_id: int, file_type: str, files_count: int, file_size_bytes: int = 0):
        """Record a PDF conversion event"""
        now = datetime.utcnow().isoformat()
        async with await self.get_connection() as db:
            await db.execute("""
                INSERT INTO conversions (user_id, file_type, files_count, file_size_bytes, timestamp)
                VALUES (?, ?, ?, ?, ?)
            """, (user_id, file_type, files_count, file_size_bytes, now))
            await db.commit()

    async def get_stats(self) -> dict:
        """Calculate and return system stats"""
        now = datetime.utcnow()
        thirty_days_ago = (now - timedelta(days=30)).isoformat()
        
        async with await self.get_connection() as db:
            # Total users
            async with db.execute("SELECT COUNT(*) FROM users") as cursor:
                total_users = (await cursor.fetchone())[0]

            # Monthly active users (active in the last 30 days)
            async with db.execute("SELECT COUNT(*) FROM users WHERE last_active_at >= ?", (thirty_days_ago,)) as cursor:
                monthly_active_users = (await cursor.fetchone())[0]

            # Total PDF conversions
            async with db.execute("SELECT COUNT(*), SUM(files_count) FROM conversions") as cursor:
                row = await cursor.fetchone()
                total_conversions = row[0] or 0
                total_files_processed = row[1] or 0

            return {
                "total_users": total_users,
                "monthly_active_users": monthly_active_users,
                "total_conversions": total_conversions,
                "total_files_processed": total_files_processed
            }

    async def get_all_users(self) -> list[int]:
        """Fetch all user IDs for broadcasting"""
        async with await self.get_connection() as db:
            async with db.execute("SELECT user_id FROM users") as cursor:
                rows = await cursor.fetchall()
                return [row[0] for row in rows]

    async def set_admin(self, user_id: int, is_admin: bool):
        """Set or unset administrator privilege for a user"""
        admin_val = 1 if is_admin else 0
        async with await self.get_connection() as db:
            await db.execute("UPDATE users SET is_admin = ? WHERE user_id = ?", (admin_val, user_id))
            await db.commit()
