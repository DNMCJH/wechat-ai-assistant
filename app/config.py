import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
CLAUDE_API_KEY = os.getenv("CLAUDE_API_KEY", "")

WECHAT_TOKEN = os.getenv("WECHAT_TOKEN", "")
WECHAT_APPID = os.getenv("WECHAT_APPID", "")
WECHAT_APPSECRET = os.getenv("WECHAT_APPSECRET", "")
MANAGER_OPENIDS = [x.strip() for x in os.getenv("MANAGER_OPENIDS", "").split(",") if x.strip()]
WECHAT_TEMPLATE_ID = os.getenv("WECHAT_TEMPLATE_ID", "")

EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "BAAI/bge-small-zh-v1.5")
FAQ_THRESHOLD = float(os.getenv("FAQ_THRESHOLD", "0.85"))
RAG_TOP_K = int(os.getenv("RAG_TOP_K", "3"))

EVAL_HIGH = float(os.getenv("EVAL_HIGH", "0.85"))
EVAL_LOW = float(os.getenv("EVAL_LOW", "0.65"))

DB_PATH = DATA_DIR / "analytics.db"
INDEX_PATH = DATA_DIR / "index.faiss"
CHUNKS_PATH = DATA_DIR / "chunks.json"
