from app.models.message import Classification
from app.services.ai_service import call_for_json
import logging

logger = logging.getLogger(__name__)

CLASSIFY_SYSTEM = """你是一个问题分类助手。请将用户问题分类到以下类别之一：
- 教务类：选课、考试、成绩、学分等
- 招生类：录取、报到、转专业等
- 资助类：奖学金、助学金、贷款等
- 生活类：宿舍、食堂、校园卡、校车、图书馆等
- 投诉类：对学校服务的不满和投诉（用户明确表达不满、要求投诉）
- 舆情类：涉及学校声誉、安全事件等
- 复杂问题：需要多部门协调或无法简单回答的问题

重要规则：
- 普通的信息咨询（如询问时间、流程、规则）都属于正常问题，needs_human 应为 false
- 只有投诉、舆情、涉及隐私安全、或确实无法自动回答的问题才设 needs_human 为 true
- confidence 表示你对分类结果的确信程度

请以JSON格式回答，包含以下字段：
- category: 分类名称
- confidence: 置信度(0-1)
- needs_human: 是否需要人工处理(true/false)
- labels: 细分标签列表"""

HUMAN_CATEGORIES = {"投诉类", "舆情类"}


async def classify(query: str) -> Classification:
    prompt = f"请对以下用户问题进行分类：\n\n{query}"
    result = await call_for_json(prompt, CLASSIFY_SYSTEM)
    logger.info(f"Classifier raw result: {result}")
    category = result.get("category", "生活类")
    confidence = float(result.get("confidence", 0.5))
    needs_human = category in HUMAN_CATEGORIES
    if category == "复杂问题" and confidence > 0.8:
        needs_human = True
    return Classification(
        category=category,
        confidence=confidence,
        needs_human=needs_human,
        labels=result.get("labels", []),
    )
