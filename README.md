# Ultra MindMap

根据文本文档生成思维导图的全栈应用。支持多种生成引擎、引擎质量对比（Bench）、文件拖放上传。

## 快速开始

### 1. 环境准备

- Python 3.11+
- Node.js 18+
- [uv](https://docs.astral.sh/uv/) (Python 包管理)

### 2. 配置

复制环境变量文件并填入你的 API Key：

```bash
cp .env.example .env
```

编辑 `.env`：

```
OPENAI_API_KEY=sk-xxx
OPENAI_API_BASE=https://api.openai.com/v1   # 可选，兼容 API 地址
```

### 3. 启动后端

```bash
cd backend
uv sync
uv run uvicorn app.main:app --reload --port 8000
```

后端运行在 http://localhost:8000，API 文档在 http://localhost:8000/docs

### 4. 启动前端

```bash
cd frontend
npm install
npx vite --port 5173
```

前端运行在 http://localhost:5173

## 引擎

| 引擎 | 适用场景 | 说明 |
|------|---------|------|
| `direct` | 中短篇文档 | 一次性发送全文给 LLM |
| `chunked` | 长篇文档 | 分块独立生成后合并 |
| `mapreduce` | 复杂长文（论文/综述） | Pre-Plan → Map(并发) → Collapse → Reduce |

## API

### 文件管理

```
POST   /api/files/upload    上传文件（支持 txt/md/pdf/docx）
GET    /api/files/           文件列表
DELETE /api/files/{file_id}  删除文件
```

### 思维导图生成

```
GET    /api/mindmap/engines   获取可用引擎列表
POST   /api/mindmap/generate  生成思维导图
```

生成请求示例：

```json
{
  "file_ids": ["xxx"],
  "engine": "direct",
  "params": {}
}
```

### 引擎对比（Bench）

```
POST   /api/bench/run   运行引擎对比
```

请求示例：

```json
{
  "file_ids": ["xxx"],
  "engine_a": "direct",
  "params_a": {},
  "engine_b": "mapreduce",
  "params_b": {},
  "judge_model": "gpt-4o"
}
```

返回每个文件的 5 维度评分（coverage / hierarchy / balance / conciseness / accuracy，各 1-5 分）。

### 设置

```
GET    /api/settings/   读取设置
POST   /api/settings/   写入设置
```

## 使用 curl 操作

上传文件：

```bash
curl -X POST http://localhost:8000/api/files/upload \
  -F "files=@your_document.pdf"
```

查看文件列表：

```bash
curl http://localhost:8000/api/files/
```

生成思维导图：

```bash
curl -X POST http://localhost:8000/api/mindmap/generate \
  -H "Content-Type: application/json" \
  -d '{"file_ids": ["FILE_ID"], "engine": "direct", "params": {}}'
```

运行 Bench 对比：

```bash
curl -X POST http://localhost:8000/api/bench/run \
  -H "Content-Type: application/json" \
  -d '{
    "file_ids": ["FILE_ID"],
    "engine_a": "direct",
    "params_a": {},
    "engine_b": "mapreduce",
    "params_b": {},
    "judge_model": "gpt-4o"
  }'
```

## 技术栈

- 后端：FastAPI + SQLAlchemy (SQLite) + OpenAI API + LangChain
- 前端：React (Vite) + TailwindCSS (CDN) + markmap + GSAP + lucide-react
