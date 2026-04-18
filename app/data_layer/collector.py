import sqlite3
import json
import logging
from datetime import datetime
from app.config import DB_PATH
from app.models.message import PipelineResult

logger = logging.getLogger(__name__)


def init_db():
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("""
        CREATE TABLE IF NOT EXISTS interactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            user_id TEXT,
            query TEXT NOT NULL,
            reply TEXT NOT NULL,
            category TEXT,
            labels TEXT,
            source TEXT,
            action TEXT,
            relevance REAL,
            correctness REAL,
            completeness REAL,
            risk REAL,
            weighted_score REAL
        )
    """)
    conn.commit()
    conn.close()


def record(user_id: str, query: str, result: PipelineResult):
    try:
        conn = sqlite3.connect(str(DB_PATH))
        eval_data = result.evaluation
        conn.execute(
            """INSERT INTO interactions
            (timestamp, user_id, query, reply, category, labels, source, action,
             relevance, correctness, completeness, risk, weighted_score)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                datetime.now().isoformat(),
                user_id,
                query,
                result.reply,
                result.category,
                json.dumps(result.labels, ensure_ascii=False),
                result.source,
                result.action,
                eval_data.relevance if eval_data else None,
                eval_data.correctness if eval_data else None,
                eval_data.completeness if eval_data else None,
                eval_data.risk if eval_data else None,
                eval_data.weighted_score if eval_data else None,
            ),
        )
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"Failed to record interaction: {e}")
