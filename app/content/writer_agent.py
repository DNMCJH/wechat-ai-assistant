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

OUTLINE_SYSTEM = """你是一个成熟的内容创作者。根据选题生成文章大纲。
标题要求：信息明确，不用感叹号，不用"必看""震惊""居然"等词。好标题像一句有信息量的话，不像广告。
以JSON格式返回：
- title: 最终标题
- summary: 一句话摘要（用于公众号推送预览，克制、有信息量）
- sections: 章节标题列表（3-5个章节，每个标题具体而非泛泛）"""

WRITER_SYSTEM = """你是一个有经验的内容创作者，写作风格成熟、克制、有信息密度。

写作原则：
- 像一个懂行的人在认真分享，不是在表演热情
- 每句话都要有信息量，删掉所有"废话"（过渡句、感叹、重复强调）
- 不用感叹号，不用"赶紧""一定要""强烈推荐"等推销语气
- 不堆砌 emoji，最多在小标题处用1-2个作为视觉标记
- 不用"宝子""家人们""绝绝子"等网络用语
- 观点要有依据，不说"据说""好像""可能"
- 段落短，一个段落只说一件事
- 用具体数据和例子代替形容词
- 文末不需要"点赞收藏转发"之类的引导"""


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
- 以一级标题开头，每个章节用二级标题
- 总字数 800-1500 字
- 信息密度优先，不要凑字数
- 不要写开头的"导语"或"引言"段，直接进入正题
- 不要在结尾写"总结"段落重复前文内容"""

    content = await generate_long_content(prompt, WRITER_SYSTEM)

    return ArticleResult(
        title=outline.title,
        summary=outline.summary,
        content=content,
        style=style.value,
        topic=topic,
    )
