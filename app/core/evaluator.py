from app.models.message import Evaluation
from app.services.ai_service import call_for_json

EVAL_SYSTEM = """你是一个AI回答质量评估助手。请从四个维度评估AI的回答质量，每个维度给出0到1的分数：

1. relevance（语义相关性）：回答是否切题，是否回答了用户的问题
2. correctness（正确性）：回答内容是否与参考资料一致，是否有事实错误
3. completeness（完整性）：回答是否完整覆盖了用户的问题
4. risk（风险等级）：0表示安全，1表示高风险。涉及敏感话题、可能引起误解、或需要人工确认的内容风险较高

请以JSON格式回答，包含 relevance, correctness, completeness, risk 四个字段，值为0-1的浮点数。"""

WEIGHTS = {
    "relevance": 0.30,
    "correctness": 0.35,
    "completeness": 0.20,
    "risk": 0.15,
}


async def evaluate(query: str, context: str, answer: str) -> Evaluation:
    prompt = (
        f"用户问题：{query}\n\n"
        f"参考资料：{context or '无'}\n\n"
        f"AI回答：{answer}\n\n"
        "请评估这个回答的质量。"
    )
    result = await call_for_json(prompt, EVAL_SYSTEM)
    relevance = float(result.get("relevance", 0.5))
    correctness = float(result.get("correctness", 0.5))
    completeness = float(result.get("completeness", 0.5))
    risk = float(result.get("risk", 0.5))
    # risk 反转：高风险应降低总分
    risk_score = 1.0 - risk
    weighted = (
        WEIGHTS["relevance"] * relevance
        + WEIGHTS["correctness"] * correctness
        + WEIGHTS["completeness"] * completeness
        + WEIGHTS["risk"] * risk_score
    )
    return Evaluation(
        relevance=relevance,
        correctness=correctness,
        completeness=completeness,
        risk=risk,
        weighted_score=round(weighted, 3),
    )
