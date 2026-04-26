import json
import logging
import httpx
from app.config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, CLAUDE_API_KEY, CLAUDE_BASE_URL

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "你是一个校园智能客服助手，负责回答学生关于学校的各类问题。"
    "请根据提供的参考资料回答问题，回答要准确、简洁、友好。"
    "如果参考资料不足以回答问题，请如实说明。"
)

FALLBACK_REPLY = "抱歉，系统暂时无法处理您的问题，请稍后再试或联系人工客服。"


async def generate_answer(query: str, context: str = "", model: str = "deepseek", history: list[dict] = None) -> str:
    prompt = query
    if context:
        prompt = f"参考资料：\n{context}\n\n用户问题：{query}"
    try:
        if model == "claude":
            return await _call_claude(prompt, history=history)
        return await _call_deepseek(prompt, history=history)
    except Exception as e:
        logger.error(f"AI call failed ({model}): {e}")
        return FALLBACK_REPLY


async def _call_deepseek(prompt: str, system: str = SYSTEM_PROMPT, timeout: int = 30, max_tokens: int = 1024, history: list[dict] = None) -> str:
    messages = [{"role": "system", "content": system}]
    if history:
        messages.extend(history)
    messages.append({"role": "user", "content": prompt})
    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.post(
            f"{DEEPSEEK_BASE_URL}/v1/chat/completions",
            headers={"Authorization": f"Bearer {DEEPSEEK_API_KEY}"},
            json={
                "model": "deepseek-chat",
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": 0.7,
            },
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]


async def _call_claude(prompt: str, history: list[dict] = None) -> str:
    if CLAUDE_BASE_URL:
        return await _call_claude_openai_compat(prompt, history=history)
    messages = []
    if history:
        messages.extend(history)
    messages.append({"role": "user", "content": prompt})
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": CLAUDE_API_KEY,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": "claude-sonnet-4-20250514",
                "max_tokens": 1024,
                "system": SYSTEM_PROMPT,
                "messages": messages,
            },
        )
        resp.raise_for_status()
        return resp.json()["content"][0]["text"]


async def _call_claude_openai_compat(prompt: str, history: list[dict] = None) -> str:
    """Call Claude via OpenAI-compatible proxy (cc switch)."""
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    if history:
        messages.extend(history)
    messages.append({"role": "user", "content": prompt})
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            f"{CLAUDE_BASE_URL}/v1/chat/completions",
            headers={"Authorization": f"Bearer {CLAUDE_API_KEY}"},
            json={
                "model": "claude-sonnet-4-20250514",
                "messages": messages,
                "max_tokens": 1024,
                "temperature": 0.7,
            },
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]


async def generate_long_content(prompt: str, system: str = "") -> str:
    """Generate long-form content with extended timeout and token limit."""
    try:
        return await _call_deepseek(
            prompt,
            system=system or SYSTEM_PROMPT,
            timeout=120,
            max_tokens=4096,
        )
    except Exception as e:
        logger.error(f"Long content generation failed: {e}")
        return ""


async def call_for_json(prompt: str, system: str = "") -> dict:
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{DEEPSEEK_BASE_URL}/v1/chat/completions",
                headers={"Authorization": f"Bearer {DEEPSEEK_API_KEY}"},
                json={
                    "model": "deepseek-chat",
                    "messages": [
                        {"role": "system", "content": system or "请以JSON格式回答"},
                        {"role": "user", "content": prompt},
                    ],
                    "max_tokens": 512,
                    "temperature": 0.1,
                    "response_format": {"type": "json_object"},
                },
            )
            resp.raise_for_status()
            text = resp.json()["choices"][0]["message"]["content"]
            return json.loads(text)
    except Exception as e:
        logger.error(f"JSON call failed: {e}")
        return {}
