# Ultra MindMap

根据文本文档生成思维导图的全栈应用。

## 技术栈

- **后端**: FastAPI + SQLAlchemy (SQLite) + OpenAI API + LangChain
- **前端**: React (Vite) + TailwindCSS (CDN) + markmap + GSAP + lucide-react

## 项目结构

```
backend/
  app/
    main.py              # FastAPI 入口, CORS, 异常处理
    database.py           # SQLite + SQLAlchemy
    models.py             # ORM 模型
    schemas.py            # Pydantic schemas
    routers/
      files.py            # 文件上传/列表/删除
      mindmap.py          # 思维导图生成 + 引擎列表
      bench.py            # 引擎质量对比 (LLM-as-judge)
    engines/
      base.py             # BaseEngine ABC + 注册表
      direct/             # 直接生成引擎
        engine.py
        prompts.py
      chunked/            # 分块生成引擎
        engine.py
        prompts.py
      docmerge/           # 多文档逐篇生成后再合并
        engine.py
        prompts.py
      outline/            # 标题层级树引擎
        engine.py         # Markdown/编号标题检测 + 层级树构建
    services/
      file_service.py     # 文件解析 (txt/md/pdf/docx)
      llm_service.py      # OpenAI API 封装 (JSON + 文本两种模式)
    utils/
      errors.py           # AppError + 异常处理器

frontend/src/
  App.jsx                 # 根组件, 状态管理, 生成/对比 tab 切换
  components/
    FileLibrary.jsx       # 文件库 (拖放上传 + 多选)
    EnginePanel.jsx       # 引擎选择 + 参数配置
    BenchPanel.jsx        # 引擎对比面板 (选引擎/运行/查看评分)
    MindMapView.jsx       # markmap 渲染
    TipCard.jsx           # 通知卡片
  services/
    api.js                # Axios API 客户端
```

## 启动方式

```bash
# 后端
cd backend
uv sync
uv run uvicorn app.main:app --reload --port 8000

# 前端
cd frontend
npm install
npx vite --port 5173
```

## 引擎系统

每个引擎是独立的 package，包含 engine.py (主逻辑) 和 prompts.py (提示词模板)。新增引擎：
1. 在 `engines/` 下创建目录
2. 继承 `BaseEngine`，实现 `get_params_schema()` 和 `generate()`
3. 调用 `register_engine()` 注册
4. 在 `engines/__init__.py` 中 import

提示词模板统一使用三引号格式：`PROMPT = """\n...\n"""`

### 现有引擎

| 引擎 | 适用场景 | 核心逻辑 |
|------|---------|---------|
| `direct` | 中短篇文档 | 一次性发送全文给 LLM |
| `chunked` | 长篇文档 | 分块独立生成后合并 |
| `docmerge` | 多篇相关文章 | 每篇先单独生成，再按主题合并 |
| `outline` | 已有清晰标题的文档 | 检测 Markdown/编号标题层级，不调用 LLM |

`llm_service.py` 提供两种 LLM 调用：
- `generate_mindmap_json()` — JSON 模式 (direct/chunked 引擎)
- `generate_mindmap_text()` — 文本模式

## Bench 模块

引擎质量对比系统，使用 LLM-as-judge 进行盲评。

- **API**: `POST /api/bench/run` — 接收 file_ids + 两个引擎配置 + judge_model
- **流程**: 两个引擎分别生成 → 随机分配 A/B 标签 → LLM 评审打分
- **评分维度**: coverage / hierarchy / balance / conciseness / accuracy (各 1-5 分)
- **前端**: BenchPanel 组件，通过左侧面板 "生成/对比" tab 切换

## 前端规范

- 亮色主题，ChatGPT 配色 (minimal + 黑白灰 + 阴影)
- Google Fonts (Inter), lucide-react 图标, GSAP 动画
- TailwindCSS 3.0+ 通过 CDN 引入
- 提示卡片用彩色左边框区分类型 (info/success/warning/error)
- 不使用 emoji 作为图标
