import re
import logging
from pathlib import Path
from app.config import DATA_DIR

logger = logging.getLogger(__name__)

TEMPLATES_DIR = DATA_DIR / "templates"


def md_to_wechat_html(markdown_text: str, template: str = "default") -> str:
    template_path = TEMPLATES_DIR / f"{template}.html"
    if template_path.exists():
        wrapper = template_path.read_text(encoding="utf-8")
    else:
        wrapper = "{content}"

    html = _convert_markdown(markdown_text)
    return wrapper.replace("{content}", html)


def _convert_markdown(text: str) -> str:
    lines = text.strip().split("\n")
    html_parts = []
    in_list = False

    for line in lines:
        stripped = line.strip()
        if not stripped:
            if in_list:
                html_parts.append("</ul>")
                in_list = False
            html_parts.append("")
            continue

        if stripped.startswith("# "):
            if in_list:
                html_parts.append("</ul>")
                in_list = False
            title = stripped[2:]
            html_parts.append(
                f'<h1 style="font-size:22px;font-weight:bold;color:#1a1a1a;'
                f'text-align:center;margin:20px 0 15px;padding-bottom:10px;'
                f'border-bottom:2px solid #07c160;">{title}</h1>'
            )
        elif stripped.startswith("## "):
            if in_list:
                html_parts.append("</ul>")
                in_list = False
            title = stripped[3:]
            html_parts.append(
                f'<h2 style="font-size:18px;font-weight:bold;color:#07c160;'
                f'margin:18px 0 10px;padding-left:10px;'
                f'border-left:4px solid #07c160;">{title}</h2>'
            )
        elif stripped.startswith("### "):
            if in_list:
                html_parts.append("</ul>")
                in_list = False
            title = stripped[4:]
            html_parts.append(
                f'<h3 style="font-size:16px;font-weight:bold;color:#333;'
                f'margin:15px 0 8px;">{title}</h3>'
            )
        elif stripped.startswith("- ") or stripped.startswith("* "):
            if not in_list:
                html_parts.append('<ul style="margin:5px 0;padding-left:20px;">')
                in_list = True
            item = _inline_format(stripped[2:])
            html_parts.append(
                f'<li style="font-size:15px;color:#555;line-height:1.8;margin:3px 0;">{item}</li>'
            )
        elif re.match(r"^\d+\.\s", stripped):
            content = re.sub(r"^\d+\.\s", "", stripped)
            content = _inline_format(content)
            if in_list:
                html_parts.append("</ul>")
                in_list = False
            html_parts.append(
                f'<p style="font-size:15px;color:#555;line-height:1.8;margin:3px 0;">{content}</p>'
            )
        elif stripped.startswith("> "):
            if in_list:
                html_parts.append("</ul>")
                in_list = False
            quote = _inline_format(stripped[2:])
            html_parts.append(
                f'<blockquote style="border-left:4px solid #07c160;padding:8px 15px;'
                f'margin:10px 0;background:#f6f6f6;color:#666;font-size:14px;">{quote}</blockquote>'
            )
        elif stripped.startswith("---"):
            if in_list:
                html_parts.append("</ul>")
                in_list = False
            html_parts.append('<hr style="border:none;border-top:1px solid #eee;margin:15px 0;">')
        else:
            if in_list:
                html_parts.append("</ul>")
                in_list = False
            para = _inline_format(stripped)
            html_parts.append(
                f'<p style="font-size:15px;color:#3f3f3f;line-height:1.8;'
                f'margin:8px 0;text-indent:0;">{para}</p>'
            )

    if in_list:
        html_parts.append("</ul>")

    return "\n".join(html_parts)


def _inline_format(text: str) -> str:
    text = re.sub(r"\*\*(.+?)\*\*", r'<strong style="color:#07c160;">\1</strong>', text)
    text = re.sub(r"\*(.+?)\*", r"<em>\1</em>", text)
    text = re.sub(
        r"`(.+?)`",
        r'<code style="background:#f0f0f0;padding:2px 5px;border-radius:3px;font-size:13px;">\1</code>',
        text,
    )
    return text
