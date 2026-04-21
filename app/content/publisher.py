import logging
import httpx
from app.config import WECHAT_APPID, WECHAT_APPSECRET

logger = logging.getLogger(__name__)

_access_token: str = ""
_token_expires: float = 0


async def _get_access_token() -> str:
    global _access_token, _token_expires
    import time
    if _access_token and time.time() < _token_expires:
        return _access_token

    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(
            "https://api.weixin.qq.com/cgi-bin/token",
            params={
                "grant_type": "client_credential",
                "appid": WECHAT_APPID,
                "secret": WECHAT_APPSECRET,
            },
        )
        data = resp.json()
    if "access_token" not in data:
        logger.error(f"Failed to get access token: {data}")
        raise RuntimeError(f"WeChat token error: {data.get('errmsg', 'unknown')}")
    _access_token = data["access_token"]
    _token_expires = time.time() + data.get("expires_in", 7200) - 300
    return _access_token


async def upload_draft(title: str, content_html: str, digest: str = "") -> str:
    """Upload article as draft via WeChat MP API. Returns media_id."""
    token = await _get_access_token()
    article = {
        "title": title,
        "content": content_html,
        "digest": digest or title,
        "show_cover_pic": 0,
        "need_open_comment": 1,
        "only_fans_can_comment": 0,
    }
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            f"https://api.weixin.qq.com/cgi-bin/draft/add?access_token={token}",
            json={"articles": [article]},
        )
        data = resp.json()
    if "media_id" not in data:
        logger.error(f"Draft upload failed: {data}")
        raise RuntimeError(f"Draft upload error: {data.get('errmsg', 'unknown')}")
    logger.info(f"Draft uploaded: {data['media_id']}")
    return data["media_id"]
