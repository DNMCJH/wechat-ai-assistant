import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.services import faq_service, rag_service
from app.data_layer.collector import init_db
from app.api.chat import router as chat_router
from app.api.wechat import router as wechat_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up...")
    init_db()
    faq_service.load_faq()
    rag_service.load_index()
    logger.info("Ready.")
    yield
    logger.info("Shutting down.")


app = FastAPI(title="校园公众号智能客服", version="1.0.0", lifespan=lifespan)
app.include_router(chat_router)
app.include_router(wechat_router)


@app.get("/health")
async def health():
    return {"status": "ok"}
