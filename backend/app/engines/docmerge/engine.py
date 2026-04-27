import json

from ..base import BaseEngine, Document, register_engine
from ...services.llm_service import generate_mindmap_json
from .prompts import MERGE_PROMPT, SINGLE_DOC_PROMPT, TREE_SECTION


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

    def _generate_single_doc_tree(self, document: Document, model: str, temperature: float, max_depth: int) -> dict:
        prompt = SINGLE_DOC_PROMPT.format(
            title=document.title,
            content=document.content,
            max_depth=max_depth,
        )
        return generate_mindmap_json(prompt, model=model, temperature=temperature)

    def _merge_doc_trees(self, trees: list[tuple[str, dict]], model: str, temperature: float, max_depth: int) -> dict:
        if len(trees) == 1:
            return trees[0][1]

        tree_sections = "\n\n".join(
            TREE_SECTION.format(
                title=title,
                tree_json=json.dumps(tree, ensure_ascii=False),
            )
            for title, tree in trees
        )
        prompt = MERGE_PROMPT.format(
            max_depth=max_depth,
            document_trees=tree_sections,
        )
        return generate_mindmap_json(prompt, model=model, temperature=temperature)

    def generate(self, documents: list[Document], params: dict) -> dict:
        model = params.get("model", "gemini-3-flash-preview")
        temperature = params.get("temperature", 0.3)
        max_depth = params.get("max_depth", 10)

        per_doc_trees = [
            (
                document.title,
                self._generate_single_doc_tree(
                    document=document,
                    model=model,
                    temperature=temperature,
                    max_depth=max_depth,
                ),
            )
            for document in documents
        ]

        return self._merge_doc_trees(
            trees=per_doc_trees,
            model=model,
            temperature=temperature,
            max_depth=max_depth,
        )


register_engine(DocMergeEngine())
