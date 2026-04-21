import sqlite3
import json
import logging
from datetime import datetime
from app.config import DATA_DIR

logger = logging.getLogger(__name__)

CONTENT_DB_PATH = DATA_DIR / "content.db"


def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(str(CONTENT_DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_content_db():
    conn = _get_conn()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS articles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            summary TEXT,
            content TEXT NOT NULL,
            style TEXT,
            topic TEXT,
            status TEXT DEFAULT 'draft',
            review_score REAL,
            review_detail TEXT,
            html_content TEXT,
            media_id TEXT,
            published_at TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS topics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            audience TEXT,
            key_points TEXT,
            reason TEXT,
            used INTEGER DEFAULT 0,
            created_at TEXT NOT NULL
        );
    """)
    conn.commit()
    conn.close()


def save_article(title: str, summary: str, content: str, style: str, topic: str) -> int:
    now = datetime.now().isoformat()
    conn = _get_conn()
    cur = conn.execute(
        """INSERT INTO articles (title, summary, content, style, topic, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (title, summary, content, style, topic, now, now),
    )
    article_id = cur.lastrowid
    conn.commit()
    conn.close()
    return article_id


def update_article(article_id: int, **kwargs):
    conn = _get_conn()
    kwargs["updated_at"] = datetime.now().isoformat()
    sets = ", ".join(f"{k} = ?" for k in kwargs)
    vals = list(kwargs.values()) + [article_id]
    conn.execute(f"UPDATE articles SET {sets} WHERE id = ?", vals)
    conn.commit()
    conn.close()


def get_article(article_id: int) -> dict | None:
    conn = _get_conn()
    row = conn.execute("SELECT * FROM articles WHERE id = ?", (article_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def list_articles(status: str | None = None, limit: int = 20) -> list[dict]:
    conn = _get_conn()
    if status:
        rows = conn.execute(
            "SELECT * FROM articles WHERE status = ? ORDER BY created_at DESC LIMIT ?",
            (status, limit),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM articles ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def save_topic(title: str, audience: str, key_points: list[str], reason: str) -> int:
    conn = _get_conn()
    cur = conn.execute(
        "INSERT INTO topics (title, audience, key_points, reason, created_at) VALUES (?, ?, ?, ?, ?)",
        (title, audience, json.dumps(key_points, ensure_ascii=False), reason, datetime.now().isoformat()),
    )
    topic_id = cur.lastrowid
    conn.commit()
    conn.close()
    return topic_id


def list_topics(unused_only: bool = False, limit: int = 20) -> list[dict]:
    conn = _get_conn()
    sql = "SELECT * FROM topics"
    if unused_only:
        sql += " WHERE used = 0"
    sql += " ORDER BY created_at DESC LIMIT ?"
    rows = conn.execute(sql, (limit,)).fetchall()
    conn.close()
    results = []
    for r in rows:
        d = dict(r)
        d["key_points"] = json.loads(d["key_points"]) if d["key_points"] else []
        results.append(d)
    return results
