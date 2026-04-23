DIRECT_PROMPT = """\
请根据以下文档内容生成思维导图。
要求：
- 最大层级深度为 {max_depth} 层
- 提取关键概念和要点，用简练文字描述
- 保持逻辑层次清晰，自由组织最合理的结构

{documents}
"""

DOC_SECTION = """\
=== 文档: {title} ===
{content}
"""
