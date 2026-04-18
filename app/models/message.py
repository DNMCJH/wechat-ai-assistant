from pydantic import BaseModel
from typing import Optional


class ChatRequest(BaseModel):
    message: str
    user_id: str = "anonymous"


class ChatResponse(BaseModel):
    reply: str
    category: str = ""
    labels: list[str] = []
    score: float = 0.0
    action: str = "auto"  # auto | confirm | human


class Classification(BaseModel):
    category: str
    confidence: float
    needs_human: bool
    labels: list[str] = []


class Evaluation(BaseModel):
    relevance: float = 0.0
    correctness: float = 0.0
    completeness: float = 0.0
    risk: float = 0.0
    weighted_score: float = 0.0


class PipelineResult(BaseModel):
    reply: str
    category: str = ""
    labels: list[str] = []
    evaluation: Optional[Evaluation] = None
    action: str = "auto"
    source: str = ""  # faq | rag_ai | human
