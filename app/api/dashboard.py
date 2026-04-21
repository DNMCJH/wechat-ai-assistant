import json
import logging
from urllib.parse import quote, unquote
from fastapi import APIRouter, Form, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from app.content import content_db
from app.content.writer_agent import generate_article
from app.content.reviewer_agent import review_article
from app.content.formatter import md_to_wechat_html
from app.content.publisher import upload_draft, PublishError
from app.content.topic_agent import generate_topics
from app.models.content import ArticleStyle

logger = logging.getLogger(__name__)
router = APIRouter(tags=["dashboard"])

STATUS_LABELS = {
    "draft": ("Draft", "#999"),
    "reviewed": ("Reviewed", "#07c160"),
    "needs_revision": ("Needs Revision", "#fa5151"),
    "formatted": ("Formatted", "#1989fa"),
    "published": ("Published", "#07c160"),
}


_CSS = """
* { margin:0; padding:0; box-sizing:border-box; }
body { font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif; background:#f5f5f5; color:#333; }
.nav { background:#fff; border-bottom:1px solid #e8e8e8; padding:0 20px; }
.nav-inner { max-width:1200px; margin:0 auto; display:flex; align-items:center; justify-content:space-between; height:56px; }
.nav-brand { font-size:18px; font-weight:600; color:#07c160; text-decoration:none; }
.nav-links a { margin-left:24px; color:#666; text-decoration:none; font-size:14px; }
.nav-links a:hover { color:#07c160; }
.main { max-width:1200px; margin:24px auto; padding:0 20px; }
.card { background:#fff; border-radius:8px; padding:24px; margin-bottom:16px; box-shadow:0 1px 3px rgba(0,0,0,.06); }
.btn { display:inline-block; padding:8px 20px; border-radius:6px; border:none; cursor:pointer; font-size:14px; text-decoration:none; color:#fff; transition:opacity .2s; }
.btn:hover { opacity:.85; }
.btn-green { background:#07c160; }
.btn-blue { background:#1989fa; }
.btn-orange { background:#ff976a; }
.btn-red { background:#fa5151; }
.btn-gray { background:#999; }
.badge { display:inline-block; padding:2px 10px; border-radius:10px; font-size:12px; color:#fff; }
table { width:100%; border-collapse:collapse; }
th,td { padding:12px 16px; text-align:left; border-bottom:1px solid #f0f0f0; }
th { font-weight:500; color:#999; font-size:13px; }
td { font-size:14px; }
tr:hover { background:#fafafa; }
.form-group { margin-bottom:16px; }
.form-group label { display:block; margin-bottom:6px; font-size:14px; color:#666; }
.form-group input,.form-group select,.form-group textarea { width:100%; padding:10px 12px; border:1px solid #ddd; border-radius:6px; font-size:14px; }
.form-group textarea { min-height:80px; resize:vertical; }
.preview-layout { display:grid; grid-template-columns:400px 1fr; gap:24px; }
.phone-frame { width:375px; border:8px solid #222; border-radius:32px; padding:20px 0; background:#fff; margin:0 auto; max-height:80vh; overflow-y:auto; }
.phone-frame::-webkit-scrollbar { width:4px; }
.phone-frame::-webkit-scrollbar-thumb { background:#ddd; border-radius:2px; }
.meta-item { margin-bottom:12px; }
.meta-label { font-size:12px; color:#999; margin-bottom:2px; }
.meta-value { font-size:14px; }
.score-bar { height:8px; border-radius:4px; background:#f0f0f0; margin-top:4px; }
.score-fill { height:100%; border-radius:4px; }
.actions { display:flex; gap:8px; margin-top:20px; flex-wrap:wrap; }
.collapsible { margin-top:16px; }
.collapsible summary { cursor:pointer; font-size:14px; color:#666; padding:8px 0; }
.collapsible pre { background:#f8f8f8; padding:16px; border-radius:6px; overflow-x:auto; font-size:13px; line-height:1.6; white-space:pre-wrap; margin-top:8px; }
.topic-card { padding:12px; border:1px solid #e8e8e8; border-radius:8px; margin-bottom:8px; cursor:pointer; transition:border-color .2s; }
.topic-card:hover { border-color:#07c160; }
.topic-title { font-weight:500; margin-bottom:4px; }
.topic-meta { font-size:12px; color:#999; }
.loading { display:none; align-items:center; gap:8px; color:#999; font-size:14px; }
.loading.active { display:flex; }
.spinner { width:16px; height:16px; border:2px solid #ddd; border-top-color:#07c160; border-radius:50%; animation:spin .6s linear infinite; }
@keyframes spin { to { transform:rotate(360deg); } }
.tabs { display:flex; gap:8px; margin-bottom:16px; }
.tab { padding:6px 16px; border-radius:16px; font-size:13px; text-decoration:none; color:#666; background:#f0f0f0; }
.tab.active { background:#07c160; color:#fff; }
.empty { text-align:center; padding:40px; color:#999; }
.toast { position:fixed; top:20px; right:20px; padding:12px 24px; border-radius:8px; color:#fff; font-size:14px; z-index:1000; animation:slideIn .3s ease, fadeOut .5s ease 3s forwards; max-width:400px; }
.toast-success { background:#07c160; }
.toast-error { background:#fa5151; }
.toast-info { background:#1989fa; }
@keyframes slideIn { from { transform:translateX(100%); opacity:0; } to { transform:translateX(0); opacity:1; } }
@keyframes fadeOut { to { opacity:0; visibility:hidden; } }
.copy-area { position:fixed; top:0; left:-9999px; }
"""


def _layout(title: str, body: str, toast: str = "", toast_type: str = "success") -> str:
    toast_html = ""
    if toast:
        toast_html = f'<div class="toast toast-{toast_type}">{toast}</div>'
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title} - Content Dashboard</title>
<style>{_CSS}</style>
</head>
<body>
{toast_html}
<nav class="nav">
  <div class="nav-inner">
    <a href="/dashboard" class="nav-brand">Content Dashboard</a>
    <div class="nav-links">
      <a href="/dashboard">Articles</a>
      <a href="/dashboard/new">New Article</a>
    </div>
  </div>
</nav>
<main class="main">{body}</main>
</body>
</html>"""


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard_list(status: str = None):
    articles = content_db.list_articles(status=status, limit=50)
    current = status or "all"

    tabs_html = ""
    for key, label in [("all", "All"), ("draft", "Draft"), ("reviewed", "Reviewed"),
                        ("formatted", "Formatted"), ("published", "Published")]:
        active = "active" if current == key else ""
        href = "/dashboard" if key == "all" else f"/dashboard?status={key}"
        tabs_html += f'<a href="{href}" class="tab {active}">{label}</a>'

    if not articles:
        rows = '<tr><td colspan="5" class="empty">No articles yet. Click "New Article" to get started.</td></tr>'
    else:
        rows = ""
        for a in articles:
            s = a.get("status", "draft")
            label, color = STATUS_LABELS.get(s, ("Unknown", "#999"))
            score = a.get("review_score")
            score_text = f"{score:.2f}" if score else "-"
            created = a.get("created_at", "")[:16].replace("T", " ")
            rows += f"""<tr onclick="location.href='/preview/{a['id']}'" style="cursor:pointer">
  <td><strong>{a['title']}</strong><br><span style="font-size:12px;color:#999">{a.get('topic','')}</span></td>
  <td><span class="badge" style="background:{color}">{label}</span></td>
  <td>{score_text}</td>
  <td>{a.get('style','')}</td>
  <td>{created}</td>
</tr>"""

    body = f"""
<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px">
  <h2 style="font-size:20px">Articles</h2>
  <a href="/dashboard/new" class="btn btn-green">+ New Article</a>
</div>
<div class="tabs">{tabs_html}</div>
<div class="card" style="padding:0">
<table>
  <thead><tr><th>Title</th><th>Status</th><th>Score</th><th>Style</th><th>Created</th></tr></thead>
  <tbody>{rows}</tbody>
</table>
</div>"""
    return HTMLResponse(_layout("Dashboard", body))


@router.get("/preview/{article_id}", response_class=HTMLResponse)
async def preview_article(article_id: int, msg: str = "", msg_type: str = "success"):
    article = content_db.get_article(article_id)
    if not article:
        return HTMLResponse(_layout("Not Found", '<div class="card empty">Article not found</div>'), status_code=404)

    s = article.get("status", "draft")
    label, color = STATUS_LABELS.get(s, ("Unknown", "#999"))

    html_content = article.get("html_content") or md_to_wechat_html(article["content"])

    phone_html = f'<div class="phone-frame">{html_content}</div>'

    meta_html = f"""
<div class="meta-item"><div class="meta-label">Status</div><div class="meta-value"><span class="badge" style="background:{color}">{label}</span></div></div>
<div class="meta-item"><div class="meta-label">Topic</div><div class="meta-value">{article.get('topic','')}</div></div>
<div class="meta-item"><div class="meta-label">Style</div><div class="meta-value">{article.get('style','')}</div></div>
<div class="meta-item"><div class="meta-label">Summary</div><div class="meta-value">{article.get('summary','')}</div></div>
<div class="meta-item"><div class="meta-label">Created</div><div class="meta-value">{article.get('created_at','')[:16].replace('T',' ')}</div></div>"""

    review_html = ""
    if article.get("review_detail"):
        try:
            rd = json.loads(article["review_detail"])
            for dim in ["accuracy", "language", "sensitivity", "readability"]:
                d = rd.get(dim, {})
                sc = d.get("score", 0)
                pct = int(sc * 100)
                bar_color = "#07c160" if sc >= 0.8 else "#ff976a" if sc >= 0.6 else "#fa5151"
                review_html += f"""<div class="meta-item">
<div class="meta-label">{dim.title()} — {sc:.2f}</div>
<div class="score-bar"><div class="score-fill" style="width:{pct}%;background:{bar_color}"></div></div>
<div style="font-size:12px;color:#999;margin-top:2px">{d.get('comment','')}</div></div>"""
            overall = rd.get("overall_score", 0)
            review_html += f'<div class="meta-item"><div class="meta-label">Overall Score</div><div class="meta-value" style="font-size:24px;font-weight:600;color:{"#07c160" if overall>=0.7 else "#fa5151"}">{overall:.3f}</div></div>'
            suggestions = rd.get("suggestions", [])
            if suggestions:
                review_html += '<div class="meta-item"><div class="meta-label">Suggestions</div><ul style="font-size:13px;color:#666;padding-left:16px">'
                for sg in suggestions:
                    review_html += f"<li>{sg}</li>"
                review_html += "</ul></div>"
        except Exception:
            pass

    actions_html = '<div class="actions">'
    if s == "draft":
        actions_html += f'<form method="post" action="/dashboard/action/review/{article_id}"><button class="btn btn-green" type="submit">Review</button></form>'
        actions_html += f'<form method="post" action="/dashboard/action/format/{article_id}"><button class="btn btn-blue" type="submit">Format</button></form>'
    elif s == "reviewed":
        actions_html += f'<form method="post" action="/dashboard/action/format/{article_id}"><button class="btn btn-blue" type="submit">Format</button></form>'
    elif s == "needs_revision":
        actions_html += f'<form method="post" action="/dashboard/action/review/{article_id}"><button class="btn btn-orange" type="submit">Re-review</button></form>'
    elif s == "formatted":
        actions_html += f'<form method="post" action="/dashboard/action/publish/{article_id}" onsubmit="return confirm(\'Upload to WeChat draft box?\')"><button class="btn btn-green" type="submit">Publish to WeChat</button></form>'
        actions_html += f'<button class="btn btn-blue" onclick="copyHtml()">Copy HTML</button>'
    elif s == "published":
        mid = article.get("media_id", "")
        actions_html += f'<div style="font-size:13px;color:#07c160;margin-bottom:8px">Published successfully</div>'
        actions_html += f'<div style="font-size:12px;color:#999">media_id: {mid}</div>'
    actions_html += f'<a href="/dashboard" class="btn btn-gray">Back</a></div>'

    escaped_html = html_content.replace("\\", "\\\\").replace("`", "\\`").replace("$", "\\$")
    copy_script = f"""<textarea class="copy-area" id="htmlSource">{html_content}</textarea>
<script>
function copyHtml() {{
  const el = document.getElementById('htmlSource');
  el.style.position = 'fixed'; el.style.left = '0'; el.style.top = '0';
  el.select(); document.execCommand('copy');
  el.style.position = 'fixed'; el.style.left = '-9999px';
  const toast = document.createElement('div');
  toast.className = 'toast toast-success';
  toast.textContent = 'HTML copied — paste into WeChat MP editor';
  document.body.appendChild(toast);
  setTimeout(() => toast.remove(), 3500);
}}
</script>"""

    md_source = article.get("content", "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    collapse_html = f'<details class="collapsible"><summary>View Markdown Source</summary><pre>{md_source}</pre></details>'

    sidebar = f"""<div class="card">
<h3 style="font-size:16px;margin-bottom:16px">{article['title']}</h3>
{meta_html}
{actions_html}
</div>
<div class="card">{review_html or '<div class="empty" style="padding:16px">Not reviewed yet</div>'}</div>
{collapse_html}"""

    body = f'<div class="preview-layout">{phone_html}<div>{sidebar}</div></div>{copy_script}'
    toast_msg = unquote(msg) if msg else ""
    return HTMLResponse(_layout(article["title"], body, toast=toast_msg, toast_type=msg_type))


@router.post("/dashboard/action/review/{article_id}")
async def action_review(article_id: int):
    article = content_db.get_article(article_id)
    if not article:
        return RedirectResponse("/dashboard", status_code=303)
    try:
        result = await review_article(article["title"], article["content"])
        status = "reviewed" if result.passed else "needs_revision"
        content_db.update_article(
            article_id,
            review_score=result.overall_score,
            review_detail=json.dumps(result.model_dump(), ensure_ascii=False),
            status=status,
        )
        msg = quote(f"Review complete — score {result.overall_score:.2f}")
        return RedirectResponse(f"/preview/{article_id}?msg={msg}", status_code=303)
    except Exception as e:
        msg = quote(f"Review failed: {e}")
        return RedirectResponse(f"/preview/{article_id}?msg={msg}&msg_type=error", status_code=303)


@router.post("/dashboard/action/format/{article_id}")
async def action_format(article_id: int):
    article = content_db.get_article(article_id)
    if not article:
        return RedirectResponse("/dashboard", status_code=303)
    html = md_to_wechat_html(article["content"])
    content_db.update_article(article_id, html_content=html, status="formatted")
    msg = quote("Formatted successfully — ready to publish or copy HTML")
    return RedirectResponse(f"/preview/{article_id}?msg={msg}", status_code=303)


@router.post("/dashboard/action/publish/{article_id}")
async def action_publish(article_id: int):
    article = content_db.get_article(article_id)
    if not article or not article.get("html_content"):
        msg = quote("Article not formatted yet")
        return RedirectResponse(f"/preview/{article_id}?msg={msg}&msg_type=error", status_code=303)
    try:
        media_id = await upload_draft(article["title"], article["html_content"], article.get("summary", ""))
        from datetime import datetime
        content_db.update_article(article_id, media_id=media_id, status="published", published_at=datetime.now().isoformat())
        msg = quote(f"Published to WeChat draft box (media_id: {media_id})")
        return RedirectResponse(f"/preview/{article_id}?msg={msg}", status_code=303)
    except PublishError as e:
        msg = quote(f"Publish failed: {e.human_message}")
        return RedirectResponse(f"/preview/{article_id}?msg={msg}&msg_type=error", status_code=303)
    except Exception as e:
        msg = quote(f"Publish failed: {e}")
        return RedirectResponse(f"/preview/{article_id}?msg={msg}&msg_type=error", status_code=303)


@router.get("/dashboard/new", response_class=HTMLResponse)
async def new_article_page():
    style_options = ""
    for s in ArticleStyle:
        labels = {"notice": "Notice / 通知公告", "guide": "Guide / 科普指南",
                  "experience": "Experience / 经验分享", "promotion": "Promotion / 活动宣传"}
        style_options += f'<option value="{s.value}">{labels.get(s.value, s.value)}</option>'

    body = f"""
<div style="display:flex;gap:24px">
<div style="flex:1">
  <div class="card">
    <h3 style="font-size:16px;margin-bottom:16px">Create New Article</h3>
    <form method="post" action="/dashboard/new" id="genForm">
      <div class="form-group">
        <label>Topic *</label>
        <input type="text" name="topic" id="topicInput" required placeholder="e.g. 本周最值得尝试的3个AI工具">
      </div>
      <div class="form-group">
        <label>Style</label>
        <select name="style">{style_options}</select>
      </div>
      <div class="form-group">
        <label>Key Points (comma separated)</label>
        <input type="text" name="key_points" placeholder="e.g. 效率提升, 免费可用, 适合大学生">
      </div>
      <div class="form-group">
        <label>Extra Context</label>
        <textarea name="extra_context" placeholder="Any additional context..."></textarea>
      </div>
      <button type="submit" class="btn btn-green" id="submitBtn">Generate Article</button>
      <div class="loading" id="loading"><div class="spinner"></div>Generating... may take 30-60s</div>
    </form>
  </div>
</div>
<div style="width:340px">
  <div class="card">
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px">
      <h4 style="font-size:14px;color:#666">Topic Suggestions</h4>
      <button class="btn btn-blue" style="padding:4px 12px;font-size:12px" onclick="fetchTopics()">Refresh</button>
    </div>
    <div id="topicList"><div class="empty" style="padding:16px;font-size:13px">Click Refresh to get AI topic suggestions</div></div>
  </div>
</div>
</div>
<script>
document.getElementById('genForm').addEventListener('submit', function() {{
  document.getElementById('submitBtn').disabled = true;
  document.getElementById('loading').classList.add('active');
}});
async function fetchTopics() {{
  const list = document.getElementById('topicList');
  list.innerHTML = '<div class="loading active"><div class="spinner"></div>Generating topics...</div>';
  try {{
    const resp = await fetch('/api/content/topics', {{
      method: 'POST', headers: {{'Content-Type': 'application/json'}},
      body: JSON.stringify({{count: 5, days: 14}})
    }});
    const data = await resp.json();
    if (!data.topics || !data.topics.length) {{ list.innerHTML = '<div class="empty" style="padding:16px;font-size:13px">No suggestions yet</div>'; return; }}
    list.innerHTML = data.topics.map(t => `<div class="topic-card" onclick="document.getElementById('topicInput').value=this.querySelector('.topic-title').textContent">
      <div class="topic-title">${{t.title}}</div>
      <div class="topic-meta">${{t.audience}} · ${{t.key_points.join(', ')}}</div>
      <div style="font-size:12px;color:#07c160;margin-top:4px">${{t.reason}}</div>
    </div>`).join('');
  }} catch(e) {{ list.innerHTML = '<div class="empty" style="padding:16px;font-size:13px;color:#fa5151">Failed to load</div>'; }}
}}
</script>"""
    return HTMLResponse(_layout("New Article", body))


@router.post("/dashboard/new")
async def create_article(
    topic: str = Form(...),
    style: str = Form("guide"),
    key_points: str = Form(""),
    extra_context: str = Form(""),
):
    points = [p.strip() for p in key_points.split(",") if p.strip()] if key_points else []
    result = await generate_article(
        topic=topic,
        style=ArticleStyle(style),
        key_points=points,
        extra_context=extra_context,
    )
    article_id = content_db.save_article(
        title=result.title, summary=result.summary,
        content=result.content, style=result.style, topic=result.topic,
    )
    return RedirectResponse(f"/preview/{article_id}", status_code=303)
