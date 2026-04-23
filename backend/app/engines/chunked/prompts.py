CHUNK_PROMPT = (
    "请根据以下文本片段生成思维导图子树。\n"
    "要求：\n"
    "- 这是文档「{doc_title}」的第 {chunk_index}/{total_chunks} 个片段\n"
    "- 最大层级深度为 {max_depth} 层\n"
    "- 提取关键概念和要点\n"
    "- 输出一个根节点，children 中包含该片段的主要主题\n\n"
    "{chunk}"
)
