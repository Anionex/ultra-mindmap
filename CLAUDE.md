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
    engines/
      base.py             # BaseEngine ABC + 注册表
      direct/             # 直接生成引擎
        engine.py
        prompts.py
      chunked/            # 分块生成引擎
        engine.py
        prompts.py
    services/
      file_service.py     # 文件解析 (txt/md/pdf/docx)
      llm_service.py      # OpenAI API 封装
    utils/
      errors.py           # AppError + 异常处理器

frontend/src/
  App.jsx                 # 根组件, 状态管理
  components/
    FileLibrary.jsx       # 文件库 (拖放上传 + 多选)
    EnginePanel.jsx       # 引擎选择 + 参数配置
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

## 前端规范

- 亮色主题，ChatGPT 配色 (minimal + 黑白灰 + 阴影)
- Google Fonts (Inter), lucide-react 图标, GSAP 动画
- TailwindCSS 3.0+ 通过 CDN 引入
- 提示卡片用彩色左边框区分类型 (info/success/warning/error)
- 不使用 emoji 作为图标
