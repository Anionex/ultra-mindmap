from .base import BaseEngine, Document, register_engine
from ..services.llm_service import generate_mindmap_json


class DirectEngine(BaseEngine):
    name = "direct"
    display_name = "直接生成"
    description = "将所有文档内容一次性发送给 LLM，直接生成完整思维导图。适合中短篇文档。"

    def get_params_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "model": {
                    "type": "string",
                    "title": "模型",
                    "enum": ["gpt-4o", "gpt-4o-mini"],
                    "default": "gpt-4o-mini",
                },
                "temperature": {
                    "type": "number",
                    "title": "温度",
                    "minimum": 0.0,
                    "maximum": 1.0,
                    "default": 0.3,
                    "step": 0.1,
                },
                "max_depth": {
                    "type": "integer",
                    "title": "最大深度",
                    "minimum": 2,
                    "maximum": 6,
                    "default": 4,
                },
            },
        }

    def generate(self, documents: list[Document], params: dict) -> dict:
        model = params.get("model", "gpt-4o-mini")
        temperature = params.get("temperature", 0.3)
        max_depth = params.get("max_depth", 4)

        doc_sections = []
        for doc in documents:
            doc_sections.append(f"=== 文档: {doc.title} ===\n{doc.content}")
        full_text = "\n\n".join(doc_sections)

        prompt = (
            f"请根据以下文档内容生成思维导图。\n"
            f"要求：\n"
            f"- 每篇文档作为根节点下的一个独立分支（以文档标题为节点名）\n"
            f"- 最大层级深度为 {max_depth} 层\n"
            f"- 提取关键概念和要点，用简练文字描述\n"
            f"- 保持逻辑层次清晰\n\n"
            f"{full_text}"
        )
        return generate_mindmap_json(prompt, model=model, temperature=temperature)


register_engine(DirectEngine())
