from langchain_text_splitters import RecursiveCharacterTextSplitter

from ..base import BaseEngine, Document, register_engine
from ...services.llm_service import generate_mindmap_json
from .prompts import CHUNK_PROMPT


class ChunkedEngine(BaseEngine):
    name = "chunked"
    display_name = "分块生成"
    description = "先将文档分块，每块独立生成思维导图后合并。适合长篇文档，能更完整地提取信息。"

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
                "chunk_size": {
                    "type": "integer",
                    "title": "分块大小",
                    "minimum": 500,
                    "maximum": 4000,
                    "default": 1500,
                    "step": 100,
                },
                "chunk_overlap": {
                    "type": "integer",
                    "title": "分块重叠",
                    "minimum": 0,
                    "maximum": 500,
                    "default": 200,
                    "step": 50,
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
        chunk_size = params.get("chunk_size", 1500)
        chunk_overlap = params.get("chunk_overlap", 200)
        max_depth = params.get("max_depth", 4)

        splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )

        root_children = []
        for doc in documents:
            chunks = splitter.split_text(doc.content)
            chunk_trees = []
            for i, chunk in enumerate(chunks):
                prompt = CHUNK_PROMPT.format(
                    doc_title=doc.title,
                    chunk_index=i + 1,
                    total_chunks=len(chunks),
                    max_depth=max_depth,
                    chunk=chunk,
                )
                tree = generate_mindmap_json(prompt, model=model, temperature=temperature)
                chunk_trees.append(tree)

            merged_children = []
            for tree in chunk_trees:
                if "children" in tree and tree["children"]:
                    merged_children.extend(tree["children"])
                elif "name" in tree:
                    merged_children.append(tree)

            root_children.append({"name": doc.title, "children": merged_children})

        return {"name": "思维导图", "children": root_children}


register_engine(ChunkedEngine())
