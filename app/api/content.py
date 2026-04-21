import json
import logging
from fastapi import APIRouter, HTTPException
from app.models.content import (
    TopicRequest, TopicListResponse, GenerateRequest, ArticleResult,
    ReviewRequest, ReviewResult, FormatRequest, PublishRequest,
)
from app.content.topic_agent import generate_topics
from app.content.writer_agent import generate_article
from app.content.reviewer_agent import review_article
from app.content.formatter import md_to_wechat_html
from app.content.publisher import upload_draft
from app.content import content_db

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/content", tags=["content"])


@router.post("/topics", response_model=TopicListResponse)
async def api_generate_topics(req: TopicRequest):
    topics = await generate_topics(count=req.count, days=req.days)
    for t in topics:
        content_db.save_topic(t.title, t.audience, t.key_points, t.reason)
    return TopicListResponse(topics=topics)


@router.post("/generate", response_model=ArticleResult)
async def api_generate_article(req: GenerateRequest):
    result = await generate_article(
        topic=req.topic,
        style=req.style,
        key_points=req.key_points,
        extra_context=req.extra_context,
    )
    article_id = content_db.save_article(
        title=result.title,
        summary=result.summary,
        content=result.content,
        style=result.style,
        topic=result.topic,
    )
    result.id = article_id
    return result


@router.post("/review", response_model=ReviewResult)
async def api_review_article(req: ReviewRequest):
    if req.article_id:
        article = content_db.get_article(req.article_id)
        if not article:
            raise HTTPException(status_code=404, detail="Article not found")
        title, content = article["title"], article["content"]
    elif req.title and req.content:
        title, content = req.title, req.content
    else:
        raise HTTPException(status_code=400, detail="Provide article_id or title+content")

    result = await review_article(title, content)

    if req.article_id:
        status = "reviewed" if result.passed else "needs_revision"
        content_db.update_article(
            req.article_id,
            review_score=result.overall_score,
            review_detail=json.dumps(result.model_dump(), ensure_ascii=False),
            status=status,
        )
    return result


@router.post("/format")
async def api_format_article(req: FormatRequest):
    if req.article_id:
        article = content_db.get_article(req.article_id)
        if not article:
            raise HTTPException(status_code=404, detail="Article not found")
        md_content = article["content"]
    elif req.content:
        md_content = req.content
    else:
        raise HTTPException(status_code=400, detail="Provide article_id or content")

    html = md_to_wechat_html(md_content, template=req.template)

    if req.article_id:
        content_db.update_article(req.article_id, html_content=html, status="formatted")

    return {"html": html, "article_id": req.article_id}


@router.post("/publish")
async def api_publish_article(req: PublishRequest):
    article = content_db.get_article(req.article_id)
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    if not article.get("html_content"):
        raise HTTPException(status_code=400, detail="Article not formatted yet, call /format first")

    media_id = await upload_draft(
        title=article["title"],
        content_html=article["html_content"],
        digest=article.get("summary", ""),
    )
    content_db.update_article(
        req.article_id,
        media_id=media_id,
        status="published",
        published_at=__import__("datetime").datetime.now().isoformat(),
    )
    return {"media_id": media_id, "article_id": req.article_id}


@router.get("/list")
async def api_list_articles(status: str = None, limit: int = 20):
    return content_db.list_articles(status=status, limit=limit)


@router.get("/drafts")
async def api_list_drafts():
    return content_db.list_articles(status="draft")


@router.get("/topics")
async def api_list_topics(unused_only: bool = False):
    return content_db.list_topics(unused_only=unused_only)
