import hashlib
import logging
import httpx
from lxml import etree
from app.config import WECHAT_TOKEN, WECHAT_APPID, WECHAT_APPSECRET

logger = logging.getLogger(__name__)

_access_token: str = ""
_token_expires: float = 0


def verify_signature(signature: str, timestamp: str, nonce: str) -> bool:
    items = sorted([WECHAT_TOKEN, timestamp, nonce])
    digest = hashlib.sha1("".join(items).encode()).hexdigest()
    return digest == signature


def parse_xml(xml_bytes: bytes) -> dict:
    root = etree.fromstring(xml_bytes)
    return {child.tag: child.text or "" for child in root}


def build_xml_reply(from_user: str, to_user: str, content: str) -> str:
    import time
    return (
        "<xml>"
        f"<ToUserName><![CDATA[{to_user}]]></ToUserName>"
        f"<FromUserName><![CDATA[{from_user}]]></FromUserName>"
        f"<CreateTime>{int(time.time())}</CreateTime>"
        "<MsgType><![CDATA[text]]></MsgType>"
        f"<Content><![CDATA[{content}]]></Content>"
        "</xml>"
    )


async def get_access_token() -> str:
    global _access_token, _token_expires
    import time
    if _access_token and time.time() < _token_expires:
        return _access_token
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            "https://api.weixin.qq.com/cgi-bin/token",
            params={
                "grant_type": "client_credential",
                "appid": WECHAT_APPID,
                "secret": WECHAT_APPSECRET,
            },
        )
        data = resp.json()
        logger.info(f"Access token response: {data}")
        _access_token = data.get("access_token", "")
        _token_expires = time.time() + data.get("expires_in", 7200) - 300
        return _access_token


async def send_customer_message(openid: str, content: str):
    token = await get_access_token()
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"https://api.weixin.qq.com/cgi-bin/message/custom/send?access_token={token}",
            json={
                "touser": openid,
                "msgtype": "text",
                "text": {"content": content},
            },
        )
        logger.info(f"Send message response: {resp.json()}")
