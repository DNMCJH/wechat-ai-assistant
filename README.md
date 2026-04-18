# WeChat Campus AI Customer Service

[中文文档](README.zh-CN.md)

An intelligent customer service system for WeChat Official Accounts, built with FastAPI. Features FAQ matching, RAG-based knowledge retrieval, multi-model routing, response quality evaluation, automatic classification, and data-driven analytics.

## Architecture

```
User Message → WeChat Official Account → Webhook
  ↓
[Classification Agent] → Categorize query
  ├── Complaint / Sensitive → Transfer to human + notify manager
  └── Normal query → AI Pipeline
        ↓
      FAQ Match → Direct answer if hit
        ↓
      RAG Retrieval → Top-k context
        ↓
      Model Router → Select model (DeepSeek / Claude)
        ↓
      AI Generation → Draft response
        ↓
      Evaluation Agent → 4-dimension scoring
        ↓
      Decision: auto-reply / reply + confirm / transfer to human
        ↓
      Data Collection → Analytics → Weekly Report
```

## Three-Layer Design

| Layer | Purpose | Modules |
|-------|---------|---------|
| ① Q&A | FAQ + RAG + multi-model | faq_service, rag_service, ai_service, router |
| ② Quality Control | Classification + evaluation + notification | classifier, evaluator, notification_service |
| ③ Analytics | Logging + statistics + reporting | collector, analyzer, reporter |

## Quick Start

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
# Fill in your API keys and WeChat config
```

### 3. Build vector index

```bash
python scripts/build_index.py
```

### 4. Start the server

```bash
uvicorn app.main:app --reload --port 8000
```

### 5. Test

```bash
# FAQ hit test
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "图书馆几点关门", "user_id": "test"}'

# RAG + AI generation test
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "奖学金评审流程是什么", "user_id": "test"}'

# Complaint classification test
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "食堂饭菜太难吃了我要投诉", "user_id": "test"}'
```

## WeChat Integration

1. Go to WeChat Official Account Platform → Development → Basic Configuration
2. Set server URL to `https://your-domain/webhook/wechat`
3. Set Token (must match `WECHAT_TOKEN` in `.env`)
4. Select "Plaintext" for message encryption
5. Configure template messages for manager notifications

## Evaluation Dimensions

| Dimension | Weight | Description |
|-----------|--------|-------------|
| Relevance | 30% | Whether the answer addresses the question |
| Correctness | 35% | Whether content matches knowledge base / facts |
| Completeness | 20% | Whether the answer fully resolves the query |
| Risk | 15% | Whether it involves sensitive content |

Decision thresholds: ≥0.80 auto-reply, 0.60~0.80 reply + notify for confirmation, <0.60 transfer to human

## Analytics

All interactions are automatically logged to SQLite, supporting:
- High-frequency question statistics
- Category trend analysis
- AI quality score analysis
- FAQ update recommendations
- Automated weekly reports

## Project Structure

```
wechat-ai-assistant/
├── app/
│   ├── main.py              # FastAPI entry point
│   ├── config.py            # Configuration
│   ├── router.py            # Model routing
│   ├── api/
│   │   ├── chat.py          # JSON API (dev/test)
│   │   └── wechat.py        # WeChat webhook (XML adapter)
│   ├── core/
│   │   ├── pipeline.py      # Main processing pipeline
│   │   ├── classifier.py    # Classification agent
│   │   └── evaluator.py     # Evaluation agent
│   ├── services/
│   │   ├── ai_service.py    # AI model calls (DeepSeek + Claude)
│   │   ├── faq_service.py   # FAQ matching
│   │   ├── rag_service.py   # RAG retrieval
│   │   ├── embedding_service.py
│   │   ├── wechat_service.py
│   │   └── notification_service.py
│   ├── data_layer/
│   │   ├── collector.py     # Data collection
│   │   ├── analyzer.py      # Statistical analysis
│   │   └── reporter.py      # Report generation
│   └── models/
│       └── message.py       # Data models
├── data/
│   ├── faq.json             # FAQ dataset
│   └── documents/           # Knowledge base documents
├── scripts/
│   └── build_index.py       # Build FAISS vector index
├── .env.example
├── requirements.txt
└── README.md
```

## Tech Stack

- Python 3.11+ / FastAPI / Pydantic
- sentence-transformers (BAAI/bge-small-zh-v1.5)
- FAISS vector search
- DeepSeek + Claude dual-model routing
- SQLite analytics storage
- WeChat Official Account API

## License

See [LICENSE](LICENSE) for details.
