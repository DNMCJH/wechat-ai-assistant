import logging
import httpx
from app.config import WECOM_WEBHOOK_URL

logger = logging.getLogger(__name__)

TITLE_MAP = {
    "complaint": "🚨 收到投诉消息",
    "public_opinion": "⚠️ 舆情预警",
    "low_score": "📉 AI回答质量偏低",
    "confirm_reply": "🔍 AI回答待确认",
    "complex": "🧩 复杂问题需人工处理",
}


async def notify_managers(event_type: str, data: dict):
    if not WECOM_WEBHOOK_URL:
        logger.warning("Manager notification skipped: WECOM_WEBHOOK_URL not set")
        return

    title = TITLE_MAP.get(event_type, "📬 新消息提醒")
    query = data.get("query", "")[:100]
    category = data.get("category", "未分类")
    score = data.get("score", "N/A")
    labels = data.get("labels", "")
    reply = data.get("reply", "")[:200]

    content = (
        f"{title}\n"
        f"> 分类：{category}\n"
        f"> 标签：{labels}\n"
        f"> 评分：{score}\n"
        f"> 用户问题：{query}\n"
    )
    if reply:
        content += f"> AI回答：{reply}\n"

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                WECOM_WEBHOOK_URL,
                json={"msgtype": "text", "text": {"content": content}},
                timeout=10,
            )
            result = resp.json()
            if result.get("errcode") != 0:
                logger.error(f"WeCom webhook failed: {result}")
    except Exception as e:
        logger.error(f"Failed to notify managers: {e}")
