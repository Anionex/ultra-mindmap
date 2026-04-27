QUALITY_JUDGING_CRITERIA = """\
生成思维导图请严格遵循以下四个核心原则：

1. 结构性（Structure）
使用清晰的层次结构
将复杂问题合理拆分为子节点
避免简单线性罗列，体现组织结构

2. 关联性（Connectivity）
节点之间必须有明确、合理的关系（如因果、依赖、解释等）
避免无关或错误连接
每个子节点都应与父节点存在明确语义关系

3. 落地性（Groundedness / Actionability）
所有叶子节点必须是“具体、可用的信息”，例如：事实\数据\明确结论可直接用于回答问题的内容
避免抽象、空泛或无实际信息的表述（如“进一步分析”、“深入研究”等）

4. 简洁性（Conciseness）
避免冗余、重复节点
控制分支数量，保证信息密度高
除原文表述，每个节点不可使用包含冒号和破折号的表达，一个节点只能是单一主体、概念（如“成功率”、“模型”）或短语（如“准确率90%”，“效果显著提升”）。
    
"""

SINGLE_DOC_PROMPT = """\
请根据以下文档内容生成一个总结型思维导图。
要求：
- 提取关键概念、论点和结构化要点，保留重要的数据和示例
- 最大层级深度为 {max_depth} 层
- 直接输出 Markdown 标题层级，使用 #、##、### 等markdown标记表示层级

    {QUALITY_JUDGING_CRITERIA}

=== 文档: {title} ===
{content}

直接输出最终思维导图，不要任何解释或额外文本。
""".replace("{QUALITY_JUDGING_CRITERIA}", QUALITY_JUDGING_CRITERIA)


MERGE_PROMPT = """\
我们已有多篇文档，并已分别生成了各自的思维导图。现在需要将这些导图整合为一个统一的最终思维导图。

约束
1. 先分析关系再组织结构。若文档主题或方法体系高度重叠 → 按主题融合，合并相近节点；若主题差异明显 → 保持为并列主分支，不强行统一抽象
2. 结构要求
   主分支使用“主题”命名，而不是文档名
   相似内容需合并去重
   每篇文档的独有信息必须保留，避免丢失或过度概括
3. 保留重要的数据和示例
4. 直接输出 Markdown 标题层级，使用 #、##、### 等markdown标记表示层级
5. 最大层级深度为：{max_depth}

    {QUALITY_JUDGING_CRITERIA}

不输出任何解释，仅输出最终思维导图

已有的文档思维导图如下：
{document_mindmaps}
""".replace("{QUALITY_JUDGING_CRITERIA}", QUALITY_JUDGING_CRITERIA)


MINDMAP_SECTION = """\
=== 文档思维导图: {title} ===
{mindmap_markdown}
"""
