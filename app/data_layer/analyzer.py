import sqlite3
from collections import Counter
from app.config import DB_PATH


def _query_db(sql: str, params: tuple = ()) -> list:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    rows = conn.execute(sql, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def top_questions(limit: int = 20, days: int = 7) -> list[dict]:
    rows = _query_db(
        """SELECT query, COUNT(*) as count FROM interactions
        WHERE timestamp >= datetime('now', ?) GROUP BY query
        ORDER BY count DESC LIMIT ?""",
        (f"-{days} days", limit),
    )
    return rows


def category_distribution(days: int = 7) -> list[dict]:
    return _query_db(
        """SELECT category, COUNT(*) as count,
        ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM interactions
            WHERE timestamp >= datetime('now', ?)), 1) as percentage
        FROM interactions WHERE timestamp >= datetime('now', ?)
        GROUP BY category ORDER BY count DESC""",
        (f"-{days} days", f"-{days} days"),
    )


def quality_stats(days: int = 7) -> dict:
    rows = _query_db(
        """SELECT
            ROUND(AVG(weighted_score), 3) as avg_score,
            COUNT(CASE WHEN action='auto' THEN 1 END) as auto_count,
            COUNT(CASE WHEN action='confirm' THEN 1 END) as confirm_count,
            COUNT(CASE WHEN action='human' THEN 1 END) as human_count,
            COUNT(*) as total
        FROM interactions WHERE timestamp >= datetime('now', ?)
        AND weighted_score IS NOT NULL""",
        (f"-{days} days",),
    )
    return rows[0] if rows else {}


def low_quality_questions(days: int = 7, limit: int = 10) -> list[dict]:
    return _query_db(
        """SELECT query, reply, weighted_score, category
        FROM interactions WHERE timestamp >= datetime('now', ?)
        AND weighted_score IS NOT NULL AND weighted_score < 0.65
        ORDER BY weighted_score ASC LIMIT ?""",
        (f"-{days} days", limit),
    )


def faq_candidates(days: int = 7, min_count: int = 3) -> list[dict]:
    return _query_db(
        """SELECT query, COUNT(*) as count, AVG(weighted_score) as avg_score
        FROM interactions WHERE timestamp >= datetime('now', ?)
        AND source = 'rag_ai' AND action = 'auto'
        GROUP BY query HAVING count >= ?
        ORDER BY count DESC""",
        (f"-{days} days", min_count),
    )
