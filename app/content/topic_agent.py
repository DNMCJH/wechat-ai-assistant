import logging
from datetime import datetime
from app.services.ai_service import call_for_json
from app.data_layer.analyzer import top_questions, category_distribution
from app.models.content import TopicSuggestion

logger = logging.getLogger(__name__)

CAMPUS_CALENDAR = {
    1: ["期末考试季", "寒假安排"],
    2: ["春季开学", "补考安排"],
    3: ["选课指南", "春招实习", "CET报名"],
    4: ["春季运动会", "转专业申请"],
    5: ["期中考试", "五一安排"],
    6: ["期末复习", "暑期实习", "CET考试"],
    7: ["暑假安排", "暑期社会实践"],
    8: ["秋季开学准备", "新生入学指南"],
    9: ["社团招新", "奖学金申请", "医保办理", "CET报名"],
    10: ["国庆安排", "体测通知", "保研推免"],
    11: ["期中考试", "秋季招聘"],
    12: ["期末复习", "CET考试", "考研冲刺"],
}

TOPIC_SYSTEM = """你是一个校园公众号选题策划专家。根据以下数据生成选题建议：
1. 学生高频问题（来自客服系统真实数据）
2. 当前校园日历节点
3. 各类别问题分布

要求：
- 选题要有实用价值，解决学生真实痛点
- 结合时效性（当前月份的校园事件）
- 标题要吸引人但不标题党
- 每个选题说明目标受众和关键要点

以JSON格式返回，包含 topics 数组，每个元素包含：
- title: 推文标题
- audience: 目标受众
- key_points: 关键要点列表
- reason: 选题理由（基于什么数据）"""


async def generate_topics(count: int = 5, days: int = 14) -> list[TopicSuggestion]:
    hot_questions = top_questions(limit=20, days=days)
    categories = category_distribution(days=days)
    month = datetime.now().month
    calendar_events = CAMPUS_CALENDAR.get(month, [])

    prompt = f"""请生成{count}个公众号推文选题建议。

## 学生高频问题（近{days}天）
{_format_questions(hot_questions)}

## 问题类别分布
{_format_categories(categories)}

## 当前校园日历节点（{month}月）
{', '.join(calendar_events) if calendar_events else '无特殊节点'}

请基于以上数据生成{count}个选题。"""

    result = await call_for_json(prompt, TOPIC_SYSTEM)
    topics = []
    for item in result.get("topics", []):
        topics.append(TopicSuggestion(
            title=item.get("title", ""),
            audience=item.get("audience", "全体学生"),
            key_points=item.get("key_points", []),
            reason=item.get("reason", ""),
        ))
    return topics[:count]


def _format_questions(questions: list[dict]) -> str:
    if not questions:
        return "暂无数据"
    lines = []
    for q in questions:
        lines.append(f"- {q['query']}（{q['count']}次）")
    return "\n".join(lines)


def _format_categories(categories: list[dict]) -> str:
    if not categories:
        return "暂无数据"
    lines = []
    for c in categories:
        lines.append(f"- {c['category']}: {c['count']}次 ({c.get('percentage', 0)}%)")
    return "\n".join(lines)
