import logging
import httpx
from app.services.wechat_service import get_access_token

logger = logging.getLogger(__name__)

WECHAT_ERROR_MESSAGES = {
    40001: "access_token 无效，请检查 AppID/AppSecret",
    40002: "不合法的凭证类型",
    48001: "当前公众号没有该接口权限（个人订阅号不支持草稿箱接口）",
    48004: "接口未被授权",
    48006: "接口已废弃",
    45009: "接口调用超过限制",
    45010: "创建菜单个数超过限制",
    87009: "草稿内容不合法",
    -1: "微信系统繁忙，请稍后重试",
}


class PublishError(Exception):
    def __init__(self, errcode: int, errmsg: str):
        self.errcode = errcode
        self.errmsg = errmsg
        human_msg = WECHAT_ERROR_MESSAGES.get(errcode, errmsg)
        super().__init__(f"[{errcode}] {human_msg}")
        self.human_message = human_msg


async def upload_draft(title: str, content_html: str, digest: str = "") -> str:
    token = await get_access_token()
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
        errcode = data.get("errcode", -1)
        errmsg = data.get("errmsg", "unknown")
        logger.error(f"Draft upload failed: {data}")
        raise PublishError(errcode, errmsg)
    logger.info(f"Draft uploaded: {data['media_id']}")
    return data["media_id"]
