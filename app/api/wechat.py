import logging
import asyncio
import time
from fastapi import APIRouter, Request, Query, BackgroundTasks, Response
from app.services.wechat_service import (
    verify_signature, parse_xml, build_xml_reply,
)
from app.services.notification_service import notify_managers
from app.core.pipeline import process_message_fast
from app.data_layer.collector import record

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/webhook", tags=["wechat"])

WECHAT_TIMEOUT = 3.0
THINKING_REPLY = "正在思考中，请稍后发送【查询】获取回答~"
CACHE_TTL = 300

_processed_msgs: dict[str, float] = {}
_pending_tasks: dict[str, asyncio.Task] = {}
_answer_cache: dict[str, tuple[str, float]] = {}


def _is_duplicate(msg_id: str) -> bool:
    now = time.time()
    expired = [k for k, v in _processed_msgs.items() if now - v > 15]
    for k in expired:
        del _processed_msgs[k]
    if msg_id in _processed_msgs:
        return True
    _processed_msgs[msg_id] = now
    return False


def _clean_cache():
    now = time.time()
    expired = [k for k, (_, t) in _answer_cache.items() if now - t > CACHE_TTL]
    for k in expired:
        del _answer_cache[k]


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


async def _process_and_cache(from_user: str, query: str):
    try:
        result = await process_message_fast(query, from_user)
        _answer_cache[from_user] = (result.reply, time.time())
        record(from_user, query, result)
        if result.action in ("human", "confirm"):
            event = "confirm_reply" if result.action == "confirm" else "complaint"
            await notify_managers(event, {
                "category": result.category,
                "query": query,
                "score": str(result.evaluation.weighted_score) if result.evaluation else "N/A",
                "labels": ", ".join(result.labels),
                "reply": result.reply,
            })
    except Exception as e:
        logger.error(f"Process failed for {from_user}: {e}")
        _answer_cache[from_user] = ("抱歉，系统暂时无法处理您的问题，请稍后再试。", time.time())
    finally:
        _pending_tasks.pop(from_user, None)


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

    _clean_cache()

    if query == "查询":
        cached = _answer_cache.pop(from_user, None)
        if cached:
            reply_xml = build_xml_reply(to_user, from_user, cached[0])
            return Response(content=reply_xml, media_type="application/xml")
        if from_user in _pending_tasks and not _pending_tasks[from_user].done():
            reply_xml = build_xml_reply(to_user, from_user, "还在思考中，请再等几秒后发送【查询】~")
            return Response(content=reply_xml, media_type="application/xml")
        reply_xml = build_xml_reply(to_user, from_user, "暂无待查询的回答，请直接提问~")
        return Response(content=reply_xml, media_type="application/xml")

    from app.services.keyword_service import match as kw_match
    kw_answer = kw_match(query)
    if kw_answer:
        reply_xml = build_xml_reply(to_user, from_user, kw_answer)
        return Response(content=reply_xml, media_type="application/xml")

    from app.services.faq_service import match
    faq_answer = match(query)
    if faq_answer:
        reply_xml = build_xml_reply(to_user, from_user, faq_answer)
        return Response(content=reply_xml, media_type="application/xml")

    task = asyncio.create_task(_process_and_cache(from_user, query))
    _pending_tasks[from_user] = task

    try:
        await asyncio.wait_for(asyncio.shield(task), timeout=WECHAT_TIMEOUT)
        cached = _answer_cache.pop(from_user, None)
        if cached:
            reply_xml = build_xml_reply(to_user, from_user, cached[0])
            return Response(content=reply_xml, media_type="application/xml")
    except asyncio.TimeoutError:
        logger.info(f"Timeout for {from_user}, returning thinking reply")

    reply_xml = build_xml_reply(to_user, from_user, THINKING_REPLY)
    return Response(content=reply_xml, media_type="application/xml")
