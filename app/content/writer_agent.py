import logging
from app.services.ai_service import generate_long_content, call_for_json
from app.services.rag_service import search as rag_search
from app.models.content import ArticleResult, ArticleOutline, ArticleStyle

logger = logging.getLogger(__name__)

STYLE_PROMPTS = {
    ArticleStyle.NOTICE: "正式、简洁、条理清晰的通知公告风格",
    ArticleStyle.GUIDE: "实用、详细、步骤清晰的科普指南风格",
    ArticleStyle.EXPERIENCE: "亲切、生动、有共鸣的经验分享风格",
    ArticleStyle.PROMOTION: "活泼、有感染力的活动宣传风格",
}

OUTLINE_SYSTEM = """你是一个校园公众号写手。根据选题生成文章大纲。
以JSON格式返回：
- title: 最终标题（可以优化原标题）
- summary: 一句话摘要（用于公众号推送预览）
- sections: 章节标题列表（3-6个章节）"""

WRITER_SYSTEM = """你是一个校园公众号写手，擅长写面向大学生的实用文章。
要求：
- 语言亲切自然，适合大学生阅读
- 信息准确，基于提供的参考资料
- 结构清晰，使用 Markdown 格式
- 每个章节200-400字
- 适当使用 emoji 增加可读性
- 文末可加互动引导（如"你还有什么问题？欢迎留言"）"""


async def generate_outline(topic: str, style: ArticleStyle, key_points: list[str] = None) -> ArticleOutline:
    style_desc = STYLE_PROMPTS.get(style, STYLE_PROMPTS[ArticleStyle.GUIDE])
    points_text = "\n".join(f"- {p}" for p in key_points) if key_points else "无特别要求"

    prompt = f"""选题：{topic}
风格要求：{style_desc}
关键要点：
{points_text}

请生成文章大纲。"""

    result = await call_for_json(prompt, OUTLINE_SYSTEM)
    return ArticleOutline(
        title=result.get("title", topic),
        summary=result.get("summary", ""),
        sections=result.get("sections", []),
    )


async def generate_article(
    topic: str,
    style: ArticleStyle = ArticleStyle.GUIDE,
    key_points: list[str] = None,
    extra_context: str = "",
) -> ArticleResult:
    outline = await generate_outline(topic, style, key_points)
    logger.info(f"Outline generated: {outline.title} ({len(outline.sections)} sections)")

    rag_results = rag_search(topic)
    for section in outline.sections:
        rag_results.extend(rag_search(section))
    seen = set()
    unique_refs = []
    for r in rag_results:
        if r not in seen:
            seen.add(r)
            unique_refs.append(r)
    context = "\n\n".join(unique_refs[:8])

    style_desc = STYLE_PROMPTS.get(style, STYLE_PROMPTS[ArticleStyle.GUIDE])
    sections_text = "\n".join(f"{i+1}. {s}" for i, s in enumerate(outline.sections))

    prompt = f"""请根据以下大纲撰写一篇完整的公众号推文。

标题：{outline.title}
风格：{style_desc}

大纲：
{sections_text}

参考资料：
{context if context else '无额外参考资料'}

{f'补充信息：{extra_context}' if extra_context else ''}

要求：
- 输出完整的 Markdown 格式文章
- 以一级标题开头
- 每个章节用二级标题
- 总字数 800-1500 字"""

    content = await generate_long_content(prompt, WRITER_SYSTEM)

    return ArticleResult(
        title=outline.title,
        summary=outline.summary,
        content=content,
        style=style.value,
        topic=topic,
    )
