from fastapi import APIRouter, BackgroundTasks
from app.models.message import ChatRequest, ChatResponse
from app.core.pipeline import process_message
from app.data_layer.collector import record

router = APIRouter(prefix="/api", tags=["chat"])


@router.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest, bg: BackgroundTasks):
    result = await process_message(req.message, req.user_id)
    bg.add_task(record, req.user_id, req.message, result)
    return ChatResponse(
        reply=result.reply,
        category=result.category,
        labels=result.labels,
        score=result.evaluation.weighted_score if result.evaluation else 0.0,
        action=result.action,
    )
