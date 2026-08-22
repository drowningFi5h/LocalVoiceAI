import json
import sqlite3
import threading
from datetime import datetime, timezone
from uuid import uuid4


def now():
    return datetime.now(timezone.utc).isoformat()


class Database:
    """Short local transactions; never hold a transaction during model/network work."""

    def __init__(self, path):
        self.conn = sqlite3.connect(path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.lock = threading.RLock()
        self.conn.executescript("""
        PRAGMA journal_mode=WAL;
        CREATE TABLE IF NOT EXISTS sources (
          id TEXT PRIMARY KEY, title TEXT NOT NULL, kind TEXT NOT NULL, url TEXT,
          path TEXT, hash TEXT, version INTEGER DEFAULT 0, status TEXT DEFAULT 'queued',
          progress INTEGER DEFAULT 0, error TEXT, chunks INTEGER DEFAULT 0, updated TEXT NOT NULL,
          generation TEXT
        );
        CREATE TABLE IF NOT EXISTS chunks (
          id TEXT PRIMARY KEY, source_id TEXT NOT NULL, version INTEGER NOT NULL,
          text TEXT NOT NULL, metadata TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS sessions (id TEXT PRIMARY KEY, created TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS turns (
          id TEXT PRIMARY KEY, session_id TEXT NOT NULL, question TEXT NOT NULL,
          answer TEXT DEFAULT '', played TEXT DEFAULT '', status TEXT DEFAULT 'running',
          mode TEXT NOT NULL, provider TEXT NOT NULL, citations TEXT DEFAULT '[]',
          trace TEXT DEFAULT '{}', created TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS evaluations (
          id TEXT PRIMARY KEY, status TEXT NOT NULL, result TEXT NOT NULL, created TEXT NOT NULL
        );
        """)
        self.conn.commit()
        if "generation" not in {row[1] for row in self.conn.execute("PRAGMA table_info(sources)")}:
            self.execute("ALTER TABLE sources ADD COLUMN generation TEXT")
        self.execute(
            "UPDATE sources SET status='error', error='Indexing interrupted. Refresh to retry.' "
            "WHERE status IN ('queued','indexing')"
        )
        self.execute("UPDATE turns SET status='interrupted' WHERE status='running'")
        self.execute("UPDATE evaluations SET status='interrupted' WHERE status='running'")

    def execute(self, sql, args=()):
        with self.lock, self.conn:
            return self.conn.execute(sql, args)

    def rows(self, sql, args=()):
        with self.lock:
            return [dict(row) for row in self.conn.execute(sql, args).fetchall()]

    def one(self, sql, args=()):
        rows = self.rows(sql, args)
        return rows[0] if rows else None

    def source(self, source_id):
        return self.one("SELECT * FROM sources WHERE id=?", (source_id,))

    def update_source(self, source_id, **fields):
        fields["updated"] = now()
        self.execute(
            "UPDATE sources SET " + ",".join(f"{key}=?" for key in fields) + " WHERE id=?",
            (*fields.values(), source_id),
        )

    def session(self):
        session_id = str(uuid4())
        self.execute("INSERT INTO sessions VALUES (?,?)", (session_id, now()))
        return session_id

    def history(self, session_id):
        rows = self.rows("SELECT * FROM turns WHERE session_id=? ORDER BY created", (session_id,))
        for row in rows:
            row["citations"] = json.loads(row["citations"])
            row["trace"] = json.loads(row["trace"])
        return rows

    def close(self):
        self.conn.close()
