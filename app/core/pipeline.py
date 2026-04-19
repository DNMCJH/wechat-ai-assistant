import asyncio
import logging
from app.models.message import PipelineResult
from app.core.classifier import classify
from app.core.evaluator import evaluate
from app.services import faq_service, rag_service
from app.services.ai_service import generate_answer
from app.router import select_model
from app.config import EVAL_HIGH, EVAL_LOW

logger = logging.getLogger(__name__)

HUMAN_REPLY = "您的问题已记录，将由人工客服为您处理，请耐心等待。"


async def process_message(query: str, user_id: str = "") -> PipelineResult:
    classification = await classify(query)
    logger.info(f"Classification: {classification.category} ({classification.confidence})")

    if classification.needs_human:
        return PipelineResult(
            reply=HUMAN_REPLY,
            category=classification.category,
            labels=classification.labels,
            action="human",
            source="human",
        )

    faq_answer = faq_service.match(query)
    if faq_answer:
        logger.info("FAQ hit")
        return PipelineResult(
            reply=faq_answer,
            category=classification.category,
            labels=classification.labels,
            action="auto",
            source="faq",
        )

    rag_results = rag_service.search(query)
    context = "\n\n".join(rag_results) if rag_results else ""

    model = select_model(query)
    logger.info(f"Using model: {model}")
    answer = await generate_answer(query, context, model)

    eval_result = await evaluate(query, context, answer)
    logger.info(f"Evaluation score: {eval_result.weighted_score}")

    if eval_result.weighted_score >= EVAL_HIGH:
        action = "auto"
    elif eval_result.weighted_score >= EVAL_LOW:
        action = "confirm"
    else:
        action = "human"
        answer = HUMAN_REPLY

    return PipelineResult(
        reply=answer,
        category=classification.category,
        labels=classification.labels,
        evaluation=eval_result,
        action=action,
        source="rag_ai",
    )


async def process_message_fast(query: str, user_id: str = "") -> PipelineResult:
    """Optimized pipeline for WeChat sync reply: parallel classify+RAG, skip eval."""
    classify_task = asyncio.create_task(classify(query))

    faq_answer = faq_service.match(query)
    if faq_answer:
        classify_task.cancel()
        return PipelineResult(reply=faq_answer, action="auto", source="faq")

    rag_results = rag_service.search(query)
    context = "\n\n".join(rag_results) if rag_results else ""

    classification = await classify_task
    logger.info(f"Classification: {classification.category} ({classification.confidence})")

    if classification.needs_human:
        return PipelineResult(
            reply=HUMAN_REPLY,
            category=classification.category,
            labels=classification.labels,
            action="human",
            source="human",
        )

    model = select_model(query)
    logger.info(f"Using model (fast): {model}")
    answer = await generate_answer(query, context, model)

    eval_result = await evaluate(query, context, answer)
    logger.info(f"Eval score (fast): {eval_result.weighted_score}")

    if eval_result.weighted_score >= EVAL_HIGH:
        action = "auto"
    elif eval_result.weighted_score >= EVAL_LOW:
        action = "confirm"
    else:
        action = "human"

    return PipelineResult(
        reply=answer,
        category=classification.category,
        labels=classification.labels,
        evaluation=eval_result,
        action=action,
        source="rag_ai",
    )
