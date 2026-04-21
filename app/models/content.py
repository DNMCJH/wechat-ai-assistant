from pydantic import BaseModel
from typing import Optional
from enum import Enum


class ArticleStyle(str, Enum):
    NOTICE = "notice"
    GUIDE = "guide"
    EXPERIENCE = "experience"
    PROMOTION = "promotion"


class TopicRequest(BaseModel):
    count: int = 5
    days: int = 14


class TopicSuggestion(BaseModel):
    title: str
    audience: str
    key_points: list[str]
    references: list[str] = []
    reason: str = ""


class TopicListResponse(BaseModel):
    topics: list[TopicSuggestion]


class GenerateRequest(BaseModel):
    topic: str
    style: ArticleStyle = ArticleStyle.GUIDE
    key_points: list[str] = []
    extra_context: str = ""


class ArticleOutline(BaseModel):
    title: str
    summary: str
    sections: list[str]


class ArticleResult(BaseModel):
    id: Optional[int] = None
    title: str
    summary: str
    content: str
    style: str
    topic: str


class ReviewRequest(BaseModel):
    article_id: Optional[int] = None
    title: str = ""
    content: str = ""


class ReviewDimension(BaseModel):
    score: float
    comment: str


class ReviewResult(BaseModel):
    accuracy: ReviewDimension
    language: ReviewDimension
    sensitivity: ReviewDimension
    readability: ReviewDimension
    overall_score: float
    passed: bool
    suggestions: list[str] = []


class FormatRequest(BaseModel):
    article_id: Optional[int] = None
    content: str = ""
    template: str = "default"


class PublishRequest(BaseModel):
    article_id: int
    scheduled_time: Optional[str] = None
