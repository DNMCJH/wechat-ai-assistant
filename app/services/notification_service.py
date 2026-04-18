import logging
import httpx
from app.config import MANAGER_OPENIDS, WECHAT_TEMPLATE_ID
from app.services.wechat_service import get_access_token

logger = logging.getLogger(__name__)


async def notify_managers(event_type: str, data: dict):
    if not MANAGER_OPENIDS or not WECHAT_TEMPLATE_ID:
        logger.warning("Manager notification skipped: missing config")
        return

    title_map = {
        "complaint": "收到投诉消息",
        "public_opinion": "舆情预警",
        "low_score": "AI回答质量偏低",
        "confirm_reply": "AI回答待确认",
        "complex": "复杂问题需人工处理",
    }
    title = title_map.get(event_type, "新消息提醒")

    template_data = {
        "first": {"value": title, "color": "#FF0000" if "complaint" in event_type else "#173177"},
        "keyword1": {"value": data.get("category", "未分类")},
        "keyword2": {"value": data.get("query", "")[:50]},
        "keyword3": {"value": data.get("score", "N/A")},
        "remark": {"value": data.get("labels", "")},
    }

    token = await get_access_token()
    async with httpx.AsyncClient() as client:
        for openid in MANAGER_OPENIDS:
            try:
                await client.post(
                    f"https://api.weixin.qq.com/cgi-bin/message/template/send?access_token={token}",
                    json={
                        "touser": openid,
                        "template_id": WECHAT_TEMPLATE_ID,
                        "data": template_data,
                    },
                )
            except Exception as e:
                logger.error(f"Failed to notify {openid}: {e}")
