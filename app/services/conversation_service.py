import time
import logging

logger = logging.getLogger(__name__)

MAX_TURNS = 10
SESSION_TTL = 1800  # 30 minutes

_sessions: dict[str, list[dict]] = {}


def _cleanup(user_id: str):
    msgs = _sessions.get(user_id)
    if not msgs:
        return
    if time.time() - msgs[-1]["ts"] > SESSION_TTL:
        del _sessions[user_id]


def add_message(user_id: str, role: str, content: str):
    if user_id not in _sessions:
        _sessions[user_id] = []
    _sessions[user_id].append({"role": role, "content": content, "ts": time.time()})
    if len(_sessions[user_id]) > MAX_TURNS:
        _sessions[user_id] = _sessions[user_id][-MAX_TURNS:]


def get_history(user_id: str) -> list[dict]:
    _cleanup(user_id)
    msgs = _sessions.get(user_id, [])
    return [{"role": m["role"], "content": m["content"]} for m in msgs]
