import logging
import asyncio
from fastapi import APIRouter, Request, Query, BackgroundTasks, Response
from app.services.wechat_service import (
    verify_signature, parse_xml, build_xml_reply, send_customer_message,
)
from app.services.notification_service import notify_managers
from app.core.pipeline import process_message
from app.data_layer.collector import record

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/webhook", tags=["wechat"])

_processed_msgs: dict[str, float] = {}


def _is_duplicate(msg_id: str) -> bool:
    import time
    now = time.time()
    # Clean expired entries
    expired = [k for k, v in _processed_msgs.items() if now - v > 15]
    for k in expired:
        del _processed_msgs[k]
    if msg_id in _processed_msgs:
        return True
    _processed_msgs[msg_id] = now
    return False


@router.get("/wechat")
async def wechat_verify(
    signature: str = Query(""),
    timestamp: str = Query(""),
    nonce: str = Query(""),
    echostr: str = Query(""),
):
    if verify_signature(signature, timestamp, nonce):
        return Response(content=echostr, media_type="text/plain")
    return Response(content="Invalid signature", status_code=403)


async def _handle_async(from_user: str, to_user: str, query: str, msg_id: str):
    try:
        result = await process_message(query, from_user)
        record(from_user, query, result)
        await send_customer_message(from_user, result.reply)
        if result.action in ("human", "confirm"):
            event = "confirm_reply" if result.action == "confirm" else "complaint"
            await notify_managers(event, {
                "category": result.category,
                "query": query,
                "score": str(result.evaluation.weighted_score) if result.evaluation else "N/A",
                "labels": ", ".join(result.labels),
            })
    except Exception as e:
        logger.error(f"Async handle failed for {msg_id}: {e}")


@router.post("/wechat")
async def wechat_message(request: Request, bg: BackgroundTasks):
    body = await request.body()
    msg = parse_xml(body)
    msg_type = msg.get("MsgType", "")
    msg_id = msg.get("MsgId", "")
    from_user = msg.get("FromUserName", "")
    to_user = msg.get("ToUserName", "")

    if msg_type != "text":
        reply = build_xml_reply(to_user, from_user, "暂时只支持文字消息哦~")
        return Response(content=reply, media_type="application/xml")

    if _is_duplicate(msg_id):
        return Response(content="success", media_type="text/plain")

    query = msg.get("Content", "").strip()
    if not query:
        return Response(content="success", media_type="text/plain")

    from app.services.faq_service import match
    faq_answer = match(query)
    if faq_answer:
        reply_xml = build_xml_reply(to_user, from_user, faq_answer)
        return Response(content=reply_xml, media_type="application/xml")

    bg.add_task(_handle_async, from_user, to_user, query, msg_id)
    return Response(content="success", media_type="text/plain")
