CHUNK_PROMPT = """\
请根据以下文本片段生成思维导图子树。
要求：
- 这是文档「{doc_title}」的第 {chunk_index}/{total_chunks} 个片段
- 最大层级深度为 {max_depth} 层
- 提取关键概念和要点
- 输出一个覆盖该片段主要主题的子树
- 直接输出 Markdown 标题层级，使用 #、##、### 表示层级

{chunk}
"""
