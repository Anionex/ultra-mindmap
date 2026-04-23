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
      mapreduce/          # MapReduce 引擎 (移植自 Open-NotebookLM)
        engine.py         # Pre-Plan → Map → Collapse → Reduce 流水线
        prompts.py        # 各阶段 prompt 模板
        utils.py          # Token 计数, JSON 解析, 节点净化, MD→JSON
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
export OPENAI_API_KEY=xxx
export OPENAI_API_BASE=xxx  # 可选
python3 -m uvicorn app.main:app --reload --port 8000

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
| `mapreduce` | 复杂长文 (论文/综述) | Pre-Plan→Map(并发)→Smart Collapse→Reduce |

### MapReduce 引擎

移植自 [Open-NotebookLM](https://github.com/Anionex/Open-NotebookLM) `feat/mapreduce-on-thinkflow` 分支。

流水线：
1. **路由**: 按 token 数判断走 direct (短文本两阶段) 还是 MapReduce (长文本)
2. **Pre-Plan**: 从标题+首尾摘录规划 5-8 个概念性主分支骨架
3. **Map**: 并发处理各 chunk，提取命名概念节点 (JSON)
4. **Smart Collapse**: 迭代合并去重节点直到 token 数在阈值内
5. **Reduce**: 综合骨架+节点+摘要渲染最终 Markdown 标题树
6. **MD→JSON**: 转换为 `{name, children}` 格式供 markmap 渲染

`llm_service.py` 提供两种 LLM 调用：
- `generate_mindmap_json()` — JSON 模式 (direct/chunked 引擎)
- `generate_mindmap_text()` — 文本模式 (mapreduce 引擎)

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
