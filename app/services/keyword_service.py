import json
import logging
from pathlib import Path
from typing import Optional
from app.config import DATA_DIR

logger = logging.getLogger(__name__)

_rules: list[dict] = []


def load_keywords():
    global _rules
    path = DATA_DIR / "keywords.json"
    if not path.exists():
        logger.warning("keywords.json not found, keyword matching disabled")
        return
    with open(path, "r", encoding="utf-8") as f:
        _rules = json.load(f)
    logger.info(f"Loaded {len(_rules)} keyword rules")


def match(query: str) -> Optional[str]:
    q = query.strip().lower()
    if not q or not _rules:
        return None
    for rule in _rules:
        mode = rule.get("mode", "contains")
        for kw in rule["keywords"]:
            kw_lower = kw.lower()
            if mode == "exact" and q == kw_lower:
                return rule["reply"]
            if mode == "contains" and kw_lower in q:
                return rule["reply"]
    return None
