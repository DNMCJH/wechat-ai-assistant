import sqlite3
from datetime import datetime, timedelta
from fastapi import APIRouter, Query
from app.config import DB_PATH

router = APIRouter(prefix="/api/stats", tags=["stats"])


def _query_db(sql: str, params: tuple = ()) -> list[dict]:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    rows = conn.execute(sql, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


@router.get("/overview")
async def overview(days: int = Query(7, ge=1, le=90)):
    since = (datetime.now() - timedelta(days=days)).isoformat()
    total = _query_db(
        "SELECT COUNT(*) as cnt FROM interactions WHERE timestamp >= ?", (since,)
    )[0]["cnt"]
    by_source = _query_db(
        "SELECT source, COUNT(*) as cnt FROM interactions WHERE timestamp >= ? GROUP BY source", (since,)
    )
    by_category = _query_db(
        "SELECT category, COUNT(*) as cnt FROM interactions WHERE timestamp >= ? GROUP BY category ORDER BY cnt DESC", (since,)
    )
    by_action = _query_db(
        "SELECT action, COUNT(*) as cnt FROM interactions WHERE timestamp >= ? GROUP BY action", (since,)
    )
    avg_score = _query_db(
        "SELECT ROUND(AVG(weighted_score), 3) as avg_score FROM interactions WHERE timestamp >= ? AND weighted_score IS NOT NULL", (since,)
    )[0]["avg_score"]
    return {
        "days": days,
        "total": total,
        "avg_score": avg_score,
        "by_source": {r["source"]: r["cnt"] for r in by_source},
        "by_category": {r["category"]: r["cnt"] for r in by_category},
        "by_action": {r["action"]: r["cnt"] for r in by_action},
    }


@router.get("/low-quality")
async def low_quality(days: int = Query(7, ge=1, le=90), threshold: float = Query(0.65)):
    since = (datetime.now() - timedelta(days=days)).isoformat()
    rows = _query_db(
        "SELECT timestamp, query, reply, category, weighted_score FROM interactions "
        "WHERE timestamp >= ? AND weighted_score IS NOT NULL AND weighted_score < ? "
        "ORDER BY weighted_score ASC LIMIT 20",
        (since, threshold),
    )
    return {"count": len(rows), "items": rows}


@router.get("/top-questions")
async def top_questions(days: int = Query(7, ge=1, le=90), limit: int = Query(10, ge=1, le=50)):
    since = (datetime.now() - timedelta(days=days)).isoformat()
    rows = _query_db(
        "SELECT query, COUNT(*) as cnt, category FROM interactions "
        "WHERE timestamp >= ? GROUP BY query ORDER BY cnt DESC LIMIT ?",
        (since, limit),
    )
    return {"items": rows}


@router.get("/weekly-report")
async def weekly_report():
    since = (datetime.now() - timedelta(days=7)).isoformat()
    total = _query_db("SELECT COUNT(*) as cnt FROM interactions WHERE timestamp >= ?", (since,))[0]["cnt"]
    avg_score = _query_db(
        "SELECT ROUND(AVG(weighted_score), 3) as v FROM interactions WHERE timestamp >= ? AND weighted_score IS NOT NULL", (since,)
    )[0]["v"]
    by_category = _query_db(
        "SELECT category, COUNT(*) as cnt FROM interactions WHERE timestamp >= ? GROUP BY category ORDER BY cnt DESC LIMIT 5", (since,)
    )
    low_count = _query_db(
        "SELECT COUNT(*) as cnt FROM interactions WHERE timestamp >= ? AND weighted_score < 0.65", (since,)
    )[0]["cnt"]
    human_count = _query_db(
        "SELECT COUNT(*) as cnt FROM interactions WHERE timestamp >= ? AND action = 'human'", (since,)
    )[0]["cnt"]
    top_qs = _query_db(
        "SELECT query, COUNT(*) as cnt FROM interactions WHERE timestamp >= ? GROUP BY query ORDER BY cnt DESC LIMIT 5", (since,)
    )

    report = (
        f"📊 智能客服周报\n"
        f"统计周期：近7天\n\n"
        f"📈 总咨询量：{total}\n"
        f"⭐ 平均质量评分：{avg_score or 'N/A'}\n"
        f"⚠️ 低质量回答：{low_count} 条\n"
        f"👤 转人工处理：{human_count} 条\n\n"
        f"🏷️ 热门分类：\n"
    )
    for r in by_category:
        report += f"  · {r['category']}：{r['cnt']} 条\n"
    report += f"\n🔥 高频问题：\n"
    for r in top_qs:
        report += f"  · {r['query'][:30]}（{r['cnt']}次）\n"

    return {"report_text": report, "total": total, "avg_score": avg_score, "low_count": low_count, "human_count": human_count}
