# 校园公众号智能客服系统

[English](README.md)

基于 FastAPI 的微信公众号 AI 客服，支持 FAQ 匹配、RAG 知识库检索、多模型路由、质量评估、自动分类分流和数据分析。

## 系统架构

```
用户消息 → 微信公众号 → Webhook
  ↓
[分类 Agent] → 判断问题类型
  ├── 投诉/舆情/复杂 → 转人工 + 通知管理者
  └── 普通问题 → AI 处理管线
        ↓
      关键词匹配 → 寒暄类秒回
        ↓
      FAQ 匹配 → 命中直接返回（语义相似度）
        ↓
      RAG 检索 → AI 生成回答（带多轮对话上下文）
        ↓
      评估 Agent → 四维度打分
        ↓
      决策：自动回复 / 回复+确认 / 转人工
        ↓
      数据记录 → 统计分析 → 周报
```

## 三层架构

| 层级 | 功能 | 模块 |
|------|------|------|
| ① 基础问答 | 关键词 + FAQ + RAG + 多模型 + 多轮对话 | keyword_service, faq_service, rag_service, ai_service, conversation_service, router |
| ② 质量控制 | 分类 + 评估 + 通知 | classifier, evaluator, notification_service |
| ③ 数据分析 | 记录 + 统计 + 周报 + 管理面板 | collector, analyzer, reporter, dashboard |

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env 填入你的 API Key 和微信配置
```

### 3. 构建向量索引

```bash
python scripts/build_index.py
```

### 4. 启动服务

```bash
uvicorn app.main:app --reload --port 8000
```

### 5. 测试

```bash
# FAQ 命中测试
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "图书馆几点关门", "user_id": "test"}'

# RAG + AI 测试
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "奖学金评审流程是什么", "user_id": "test"}'

# 投诉分类测试
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "食堂饭菜太难吃了我要投诉", "user_id": "test"}'
```

## 微信公众号接入

1. 在微信公众平台 → 开发 → 基本配置中设置服务器地址为 `https://你的域名/webhook/wechat`
2. 填入 Token（与 .env 中 WECHAT_TOKEN 一致）
3. 消息加解密方式选择"明文模式"
4. 配置模板消息用于管理者通知

## 评估维度

| 维度 | 权重 | 说明 |
|------|------|------|
| 语义相关性 | 30% | 回答是否切题 |
| 正确性 | 35% | 内容是否与事实匹配 |
| 完整性 | 20% | 是否完整解决问题 |
| 风险评估 | 15% | 是否涉及敏感内容 |

决策阈值：≥0.85 自动回复，0.65~0.85 回复+通知确认，<0.65 转人工

## 数据分析

系统自动记录所有交互数据到 SQLite，支持：
- 高频问题统计
- 分类趋势分析
- AI 质量评分分析
- FAQ 更新建议
- 自动生成周报

## 项目结构

```
wechat-ai-assistant/
├── app/
│   ├── main.py              # FastAPI 入口
│   ├── config.py            # 配置管理
│   ├── router.py            # 模型路由
│   ├── api/
│   │   ├── chat.py          # JSON API
│   │   └── wechat.py        # 微信 webhook
│   ├── core/
│   │   ├── pipeline.py      # 主处理管线
│   │   ├── classifier.py    # 分类 Agent
│   │   └── evaluator.py     # 评估 Agent
│   ├── services/
│   │   ├── ai_service.py    # AI 模型调用
│   │   ├── faq_service.py   # FAQ 匹配
│   │   ├── keyword_service.py # 关键词快速回复
│   │   ├── conversation_service.py # 多轮对话记忆
│   │   ├── rag_service.py   # RAG 检索
│   │   ├── embedding_service.py
│   │   ├── wechat_service.py
│   │   └── notification_service.py
│   ├── data_layer/
│   │   ├── collector.py     # 数据收集
│   │   ├── analyzer.py      # 统计分析
│   │   └── reporter.py      # 周报生成
│   └── models/
│       └── message.py       # 数据模型
├── data/
│   ├── faq.json             # FAQ 数据
│   ├── keywords.json        # 关键词快速回复规则
│   └── documents/           # 知识库文档
├── scripts/
│   └── build_index.py       # 构建向量索引
├── .env.example
├── requirements.txt
└── README.md
```

## 技术栈

- Python 3.11+ / FastAPI / Pydantic
- sentence-transformers (BAAI/bge-small-zh-v1.5)
- FAISS 向量检索
- DeepSeek + Claude 双模型
- SQLite 数据存储
- 微信公众号 API
