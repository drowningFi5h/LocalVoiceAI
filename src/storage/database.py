from pathlib import Path
import sqlite3

from core.config import Config


class Database:

    def __init__(self):

        cfg = Config()

        path = cfg.database["path"]

        Path(path).parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        self.connection = sqlite3.connect(path)

        self.connection.row_factory = sqlite3.Row

        self.initialize()

    def initialize(self) -> None:

        cursor = self.connection.cursor()

        cursor.executescript(
            """
            CREATE TABLE IF NOT EXISTS memories (

                id INTEGER PRIMARY KEY AUTOINCREMENT,

                memory_type TEXT NOT NULL,

                category TEXT,

                key TEXT,

                value TEXT,

                importance REAL DEFAULT 0.5,

                confidence REAL DEFAULT 1.0,

                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,

                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,

                last_used DATETIME,

                use_count INTEGER DEFAULT 0

            );

            CREATE INDEX IF NOT EXISTS idx_memory_type
            ON memories(memory_type);

            CREATE INDEX IF NOT EXISTS idx_key
            ON memories(key);
            """
        )

        self.connection.commit()

    def close(self) -> None:

        self.connection.close()