"""\
MapReduce 引擎的 Prompt 模板。
移植自 Open-NotebookLM (feat/mapreduce-on-thinkflow 分支)。
"""

_BRANCH_RULES_ZH = """\
**主分支命名硬约束（违反则立刻重写）**：
- 主分支（##）必须是"概念主题 / 方法模块 / 问题域 / 应用领域 / 关键发现"
- 严禁出现以下"叙事脚手架"作为主分支：背景介绍、研究背景、发展历程、演进历程、技术演进、章节概览、文章结构、章节安排、前沿方向、未来展望、未来趋势、未来工作、研究展望、相关综述、综述对比、挑战与展望、总结与展望、引言、结论、附录、参考文献、致谢
- 严禁以"年份 / 时间 / 顺序"作为分类轴
- 严禁出现"核心问题 / 解决方案 / 关键发现 / 主要内容 / 研究方法 / 主要贡献"这类空壳容器节点，必须用具体的概念词替代
- 主分支应当具备信息密度：让读者看到主分支名就能猜到大致内容
"""

_NAMING_RULES_ZH = """\
**节点命名规则**：
1. 每个节点 3–12 个字的短语；优先使用方法名 / 现象名 / 任务名 / 模型名 / 关键术语
2. 严禁在节点名中使用括号补说
3. 严禁孤立的"年份 / 百分比 / 数字 / 金额"作为节点名
4. 严禁把作者所属机构、期刊卷号、会议名、arxiv 编号、页码等元信息作为节点
5. 专有名词（如 Transformer、DQN、AlphaGo、MoE、Diffusion、CLIP）保持英文 / 数学符号原形，不要翻译
"""


def build_single_pass_prompt(contents_str: str, language: str, max_depth: int) -> str:
    return f"""你是一位经验丰富的知识结构分析师 + 思维导图设计师。请把下面这篇（或这几份）文档读完，然后像人类专家那样画一张层级清晰的思维导图。

## 你应该模拟的"画图思路"
1. **先通读全文，识别真正的主题**：这篇文章在讲哪几个概念 / 方法 / 问题 / 应用？跨章节归并相同主题。
2. **规划主分支（##）**：先在脑中确定 5–8 个能够代表全文的"概念性主分支"，再开始往下展开。一定不要按章节顺序或时间顺序作为主轴。
3. **每个主分支下，挂上具体的命名概念 / 方法 / 子主题（###）**。
4. **细节、数据、年份做为叶子（####+）**：以"概念→属性"的方式呈现。

{_BRANCH_RULES_ZH}

{_NAMING_RULES_ZH}

## 全文覆盖与均衡硬约束
- **主分支恰好 5–8 个**
- **每个主分支下总节点数控制在 10–25 个**
- **不能遗漏文章的任何主要主题板块**
- 如果输入是多份文档，必须均衡覆盖每份文档的核心

## 信息保真硬约束
- 关键定量数据必须保留——但作为叶子节点的描述短语
- 重点保留命名概念：模型名、算法名、数据集名、任务名、关键术语

## 整体深度
- 整体最多 {max_depth} 层（# 到 {'#' * max_depth}）

## 语言
- 输出节点的文字使用 **{language}** 语言
- 但专有名词保持英文原形

## 输出格式
- 纯 Markdown 标题结构（# 根节点，## 主分支，### 子主题，#### 及以下）
- 不要使用代码围栏、列表符号或其他 Markdown 格式
- 不要输出任何解释文字，直接从根节点开始

## 文档内容
{contents_str}

请直接输出 Markdown 思维导图："""


def build_analyze_structure_prompt(contents_str: str, language: str, max_depth: int) -> str:
    return f"""你是一位资深知识结构分析师。请阅读以下文档，然后输出一份层级化知识结构。

## 分析方法
1. 先通读，再综合：识别真正的主题、概念、方法、应用、关键发现；跨文档把相近主题归并。
2. 规划 5–8 个概念性主分支，覆盖全文的主要内容板块。
3. 每个主分支下展开命名子概念，最多 {max_depth} 层。
4. 细节信息以子节点形式挂在对应概念下。

{_BRANCH_RULES_ZH}

{_NAMING_RULES_ZH}

## 输出格式
- 每行一个节点；用缩进（2 空格）表示层级
- 第一行是根节点（不缩进），覆盖全文主旨（≤ 15 字）
- 不要输出解释文字，不要使用 Markdown 标题符号 #
- 使用 **{language}** 语言（专有名词保持原形）

## 文档内容
{contents_str}

请直接输出层级化知识结构："""


def build_render_structure_prompt(structure: str, language: str, max_depth: int) -> str:
    return f"""你是一位思维导图设计师。请把下面的层级化知识结构渲染为 Markdown 标题树。

## 渲染规则
1. 根节点用 `# `，第二层 `## `，第三层 `### `，依此类推（最多 {max_depth} 层）
2. 严格按照输入结构的层级渲染；可以微调措辞使节点更简洁，但不要新增 / 删除 / 重排主分支
3. 节点名 3–12 字短语；专有名词保留原形
4. 不要使用代码围栏，不要输出解释文字
5. 使用 **{language}** 语言

{_NAMING_RULES_ZH}

## 输入：层级化知识结构
{structure}

请直接输出 Markdown 思维导图："""


def build_pre_plan_prompt(headings_md: str, excerpt: str, language: str) -> str:
    lang_instruction = "使用中文" if language == "zh" else f"Output in {language}"
    headings_block = headings_md.strip() or "(原文未提供标题结构)"
    excerpt_block = excerpt.strip() or "(无摘录)"

    return f"""你是一位思维导图架构师。请阅读下面的原文标题和首尾摘录，规划 5–8 个概念性主分支作为全局骨架。

## 输入 A：原文标题结构
{headings_block}

## 输入 B：首尾摘录
{excerpt_block}

## 你要做的
基于上述信息，决定这份导图的 5–8 个概念性主分支。每个主分支需要给出：
1. `name`：主分支名（3–12 字短语）
2. `gist`：一句话描述（≤ 30 字）
3. `keywords`：5–12 个该分支下应包含的具体子概念

{_BRANCH_RULES_ZH}

{_NAMING_RULES_ZH}

## 语言
- `name` 和 `keywords` 都使用 **{language}** 语言；专有名词保持英文原形
- {lang_instruction}

## 输出格式（仅输出合法 JSON 数组，不含解释或代码围栏）
[
  {{"name": "主分支名", "gist": "一句话描述", "keywords": ["子概念1", "子概念2", ...]}},
  ...
]

请直接输出 JSON 数组："""


def build_map_prompt(chunk: dict, language: str, skeleton_json: str = "") -> str:
    chunk_id = chunk["chunk_id"]
    source = chunk["source"]
    text = chunk["text"]

    lang_instruction = "使用中文" if language == "zh" else f"Use {language} language"

    skeleton_section = ""
    if skeleton_json.strip():
        skeleton_section = f"""
## 全局骨架（来自 Pre-Plan；抽取时对齐）
{skeleton_json}
"""

    return f"""你是一位知识抽取专家。阅读下面这段文本，先写一段片段摘要，再提取核心命名概念作为节点列表。
{skeleton_section}

## 节点 = 命名概念，不是描述句
- 节点 topic 必须是命名实体 / 方法名 / 模型名 / 算法名 / 任务名 / 概念名（3–12 字短语）

## 数字 / 数据如何处理
- 数字、年份、百分比等只能写在 summary 字段里，不能作为 topic

## 父子层级
- parent_topic 可以为 `ROOT` 或上层节点的 topic 字符串

## 提取数量
- 目标 12–25 个节点

## 专有名词
- Transformer / DQN / CLIP 等保留英文原形

## 语言
- summary 字段 {lang_instruction}；topic 字段对中文术语用中文，对英文术语用英文原形

## 输出格式（仅输出合法 JSON 对象，不含解释或代码围栏）
{{
  "summary": "2-4 句话的片段摘要",
  "nodes": [
    {{
      "node_id": "{chunk_id}_n0",
      "topic": "命名概念（3-12 字）",
      "parent_topic": "ROOT 或上层 topic",
      "summary": "1-2 句话描述",
      "importance_score": 5,
      "source_chunk_id": "{chunk_id}"
    }}
  ]
}}

## 文本片段（来自: {source}，片段ID: {chunk_id}）
---
{text}
---

请直接输出 JSON 对象："""


def build_collapse_prompt(group_a_json: str, group_b_json: str, language: str) -> str:
    lang_instruction = "使用中文输出" if language == "zh" else f"Output in {language}"

    return f"""你是知识结构整合专家。请将以下两组节点合并去重。

## 合并原则（保守原则，宁多勿合）
1. 只合并真正同义的节点
2. 不同方法绝不合并
3. 数据保留：合并节点时，两侧 summary 中的数据必须合并保留
4. 质量优先，宁多勿合
5. 保持 topic 是命名概念
6. 建立父子关系
7. node_id 重新编为 `merged_n0`、`merged_n1`...
8. {lang_instruction}

## 输出格式
仅输出合法 JSON 数组，不含解释或代码围栏。每个节点：
{{"node_id": "merged_nX", "topic": "...", "parent_topic": "ROOT或上级topic", "summary": "...", "importance_score": 1-5, "source_chunk_id": "..."}}

## 节点组 A
{group_a_json}

## 节点组 B
{group_b_json}

请直接输出合并后的 JSON 数组："""


def build_reduce_prompt(
    chunk_summaries: list[dict],
    headings_md: str,
    retained_nodes_json: str,
    language: str,
    max_depth: int,
    skeleton_json: str = "",
    source_excerpt: str = "",
) -> str:
    lang_instruction = f"使用 {language} 输出" if language != "zh" else "使用中文输出"

    summary_block = "\n".join(
        f"- [{it.get('chunk_id', '')}] {it.get('summary', '')}"
        for it in chunk_summaries if it.get("summary")
    ) or "(无可用片段摘要)"

    headings_block = headings_md.strip() or "(原文未提供标题结构)"
    skeleton_block = skeleton_json.strip() or "(未提供骨架，请基于摘要 + 标题自己规划 5–8 个主分支)"

    source_section = ""
    if source_excerpt.strip():
        source_section = f"""
## 输入 E：原文（节选）
{source_excerpt}
"""

    return f"""你是一位思维导图设计师。请综合下面信息，生成一份层级清晰的思维导图（Markdown 标题树）。

## 输入 A：主分支骨架
{skeleton_block}

## 输入 B：各片段摘要
{summary_block}

## 输入 C：原文标题结构
{headings_block}

## 输入 D：保留的命名节点
{retained_nodes_json}
{source_section}

## 生成规则
1. 根节点（#）：≤ 15 字短语，覆盖全文主旨
2. 主分支（##）：严格按输入 A 的 skeleton 来
3. 子层级（###+）：严格使用 retained_nodes 中的 topic 作为节点名
4. 节点名必须是命名实体
5. 节点数紧凑：总节点数 60–100 个
6. 数据点不作为节点名
7. 严禁同义重复
8. 整体最多 {max_depth} 层
9. {lang_instruction}

{_BRANCH_RULES_ZH}

{_NAMING_RULES_ZH}

## 输出格式
- 纯 Markdown 标题结构
- 不使用代码围栏 / 列表符号
- 不输出解释文字，直接从根节点开始

请直接输出思维导图："""


def build_merge_prompt(article_markdowns: list[dict], language: str, max_depth: int) -> str:
    lang_instruction = f"使用 {language} 输出" if language != "zh" else "使用中文输出"

    parts = []
    for i, item in enumerate(article_markdowns, 1):
        fn = item.get("filename", f"article_{i}")
        md = item.get("markdown", "").strip()
        parts.append(f"## 文章 {i}：{fn}\n{md}")
    combined = "\n\n".join(parts)

    return f"""你是一位思维导图整合专家。下方给出多份已生成的思维导图，请将它们合并为一份更大的思维导图。

## 合并规则
1. 新根节点（#）：覆盖所有文章共同主旨的短语，≤ 20 字
2. 每篇文章降级为主分支（##）
3. 跨文章主题合并
4. 主分支数量：最多 10 个
5. 总节点数：≤ 200 个
6. 深度上限：{max_depth} 层
7. {lang_instruction}

## 输入
{combined}

## 输出
- 纯 Markdown 标题结构
- 不使用代码围栏或解释文字
- 直接从根节点开始

请直接输出合并后的思维导图："""


def build_beautify_prompt(markdown: str, language: str, max_depth: int) -> str:
    lang_instruction = f"使用 {language} 输出" if language != "zh" else "使用中文输出"
    return f"""你是思维导图润色专家。请对下方思维导图做一次美化。

## 美化要求
1. 结构重平衡：主分支控制在 5–8 个
2. 命名优化：节点 3–12 字短语
3. 删除"叙事脚手架"主分支
4. 信息保真：不要删除具体事实和数据
5. {lang_instruction}

## 输入
{markdown}

## 输出
- 纯 Markdown 标题结构
- 不使用代码围栏 / 解释文字
- 直接从根节点开始

请直接输出美化后的思维导图："""
