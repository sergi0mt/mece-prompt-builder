"""Async SQLite database connection and migration runner."""
import aiosqlite
from pathlib import Path
from .config import get_settings

settings = get_settings()
DB_PATH = settings.database_path
MIGRATIONS_DIR = Path(__file__).parent / "migrations"


async def get_db() -> aiosqlite.Connection:
    """Get a database connection. Caller must close it."""
    db = await aiosqlite.connect(DB_PATH)
    db.row_factory = aiosqlite.Row
    await db.execute("PRAGMA journal_mode=WAL")
    await db.execute("PRAGMA foreign_keys=ON")
    return db


async def init_db():
    """Run all migration SQL files in order."""
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)

    db = await get_db()
    try:
        # Track applied migrations
        await db.execute("""
            CREATE TABLE IF NOT EXISTS _migrations (
                name TEXT PRIMARY KEY,
                applied_at TEXT DEFAULT (datetime('now'))
            )
        """)

        # Run pending migrations
        migration_files = sorted(MIGRATIONS_DIR.glob("*.sql"))
        for mf in migration_files:
            cursor = await db.execute(
                "SELECT 1 FROM _migrations WHERE name = ?", (mf.name,)
            )
            if await cursor.fetchone():
                continue

            sql = mf.read_text(encoding="utf-8")
            await db.executescript(sql)
            await db.execute(
                "INSERT INTO _migrations (name) VALUES (?)", (mf.name,)
            )
            print(f"  Applied migration: {mf.name}")

        await db.commit()
    finally:
        await db.close()
