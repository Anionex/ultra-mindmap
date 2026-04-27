from ..base import BaseEngine, Document, register_engine
from ...services.llm_service import generate_mindmap_markdown
from ...services.mindmap_format import normalize_mindmap_payload
from .prompts import MERGE_PROMPT, MINDMAP_SECTION, SINGLE_DOC_PROMPT


class DocMergeEngine(BaseEngine):
    name = "docmerge"
    display_name = "逐篇生成后合并"
    description = "每篇文档先单独生成思维导图，再将多篇文档的导图合并成最终结果。"

    def get_params_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "model": {
                    "type": "string",
                    "title": "模型",
                    "default": "gemini-3-flash-preview",
                },
                "temperature": {
                    "type": "number",
                    "title": "温度",
                    "default": 0.3,
                    "step": 0.1,
                },
                "max_depth": {
                    "type": "integer",
                    "title": "最大深度",
                    "default": 10,
                },
            },
        }

    def _generate_single_doc_mindmap(self, document: Document, model: str, temperature: float, max_depth: int) -> str:
        prompt = SINGLE_DOC_PROMPT.format(
            title=document.title,
            content=document.content,
            max_depth=max_depth,
        )
        return generate_mindmap_markdown(prompt, model=model, temperature=temperature).strip()

    def _merge_doc_mindmaps(self, mindmaps: list[tuple[str, str]], model: str, temperature: float, max_depth: int) -> dict:
        if len(mindmaps) == 1:
            return normalize_mindmap_payload(mindmaps[0][1])

        mindmap_sections = "\n\n".join(
            MINDMAP_SECTION.format(
                title=title,
                mindmap_markdown=mindmap_markdown,
            )
            for title, mindmap_markdown in mindmaps
        )
        prompt = MERGE_PROMPT.format(
            max_depth=max_depth,
            document_mindmaps=mindmap_sections,
        )
        markdown = generate_mindmap_markdown(prompt, model=model, temperature=temperature)
        return normalize_mindmap_payload(markdown)

    def generate(self, documents: list[Document], params: dict) -> dict:
        model = params.get("model", "gemini-3-flash-preview")
        temperature = params.get("temperature", 0.3)
        max_depth = params.get("max_depth", 10)

        per_doc_mindmaps = [
            (
                document.title,
                self._generate_single_doc_mindmap(
                    document=document,
                    model=model,
                    temperature=temperature,
                    max_depth=max_depth,
                ),
            )
            for document in documents
        ]

        return self._merge_doc_mindmaps(
            mindmaps=per_doc_mindmaps,
            model=model,
            temperature=temperature,
            max_depth=max_depth,
        )


register_engine(DocMergeEngine())
