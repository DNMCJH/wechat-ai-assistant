from datetime import datetime
from app.data_layer import analyzer


def generate_weekly_report() -> str:
    quality = analyzer.quality_stats(days=7)
    categories = analyzer.category_distribution(days=7)
    top_q = analyzer.top_questions(limit=10, days=7)
    low_q = analyzer.low_quality_questions(days=7, limit=5)
    faq_cands = analyzer.faq_candidates(days=7)

    lines = [
        f"# 智能客服周报 ({datetime.now().strftime('%Y-%m-%d')})",
        "",
        "## 整体数据",
        f"- 总交互数：{quality.get('total', 0)}",
        f"- 平均质量评分：{quality.get('avg_score', 'N/A')}",
        f"- 自动处理：{quality.get('auto_count', 0)}",
        f"- 需确认：{quality.get('confirm_count', 0)}",
        f"- 转人工：{quality.get('human_count', 0)}",
        "",
        "## 分类分布",
    ]
    for cat in categories:
        lines.append(f"- {cat['category']}：{cat['count']}次 ({cat['percentage']}%)")

    lines.extend(["", "## 高频问题 Top 10"])
    for i, q in enumerate(top_q, 1):
        lines.append(f"{i}. [{q['count']}次] {q['query']}")

    if low_q:
        lines.extend(["", "## 低质量回答（需关注）"])
        for q in low_q:
            lines.append(f"- [{q['weighted_score']:.2f}] {q['query']}")

    if faq_cands:
        lines.extend(["", "## FAQ 更新建议", "以下高频问题建议加入FAQ："])
        for q in faq_cands:
            lines.append(f"- [{q['count']}次, 评分{q['avg_score']:.2f}] {q['query']}")

    lines.extend(["", "## 优化建议"])
    total = quality.get("total", 1) or 1
    human_rate = quality.get("human_count", 0) / total
    if human_rate > 0.3:
        lines.append("- 转人工比例偏高，建议补充知识库内容")
    avg = quality.get("avg_score")
    if avg and avg < 0.75:
        lines.append("- 平均质量评分偏低，建议检查RAG知识库覆盖度")
    if faq_cands:
        lines.append(f"- 有 {len(faq_cands)} 个高频问题可加入FAQ以提升响应速度")

    return "\n".join(lines)
