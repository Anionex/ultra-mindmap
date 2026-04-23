CHUNK_PROMPT = """\
请根据以下文本片段生成思维导图子树。
要求：
- 这是文档「{doc_title}」的第 {chunk_index}/{total_chunks} 个片段
- 最大层级深度为 {max_depth} 层
- 提取关键概念和要点
- 输出一个根节点，children 中包含该片段的主要主题

{chunk}
"""
