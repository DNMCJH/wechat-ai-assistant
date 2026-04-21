import logging
from app.services.ai_service import call_for_json
from app.models.content import ReviewResult, ReviewDimension

logger = logging.getLogger(__name__)

REVIEW_THRESHOLD = 0.7

REVIEW_SYSTEM = """你是一个内容审核专家，负责评估校园公众号推文的质量。
请从以下四个维度评估，每个维度给出0-1的分数和简短评语：

1. accuracy（事实准确性）：内容是否准确，有无事实错误或误导信息
2. language（语言质量）：文笔是否流畅，语法是否正确，表达是否得体
3. sensitivity（敏感内容）：是否包含敏感、争议或不当内容（0=有问题，1=安全）
4. readability（可读性）：结构是否清晰，是否易于阅读，排版是否合理

以JSON格式返回：
- accuracy: {"score": 0-1, "comment": "评语"}
- language: {"score": 0-1, "comment": "评语"}
- sensitivity: {"score": 0-1, "comment": "评语"}
- readability: {"score": 0-1, "comment": "评语"}
- suggestions: 修改建议列表"""


async def review_article(title: str, content: str) -> ReviewResult:
    prompt = f"""请审核以下公众号推文：

标题：{title}

正文：
{content}

请给出详细评估。"""

    result = await call_for_json(prompt, REVIEW_SYSTEM)

    def _parse_dim(data) -> ReviewDimension:
        if isinstance(data, dict):
            return ReviewDimension(
                score=float(data.get("score", 0.5)),
                comment=data.get("comment", ""),
            )
        return ReviewDimension(score=float(data) if data else 0.5, comment="")

    accuracy = _parse_dim(result.get("accuracy"))
    language = _parse_dim(result.get("language"))
    sensitivity = _parse_dim(result.get("sensitivity"))
    readability = _parse_dim(result.get("readability"))

    overall = (
        accuracy.score * 0.35
        + language.score * 0.20
        + sensitivity.score * 0.25
        + readability.score * 0.20
    )

    return ReviewResult(
        accuracy=accuracy,
        language=language,
        sensitivity=sensitivity,
        readability=readability,
        overall_score=round(overall, 3),
        passed=overall >= REVIEW_THRESHOLD,
        suggestions=result.get("suggestions", []),
    )
