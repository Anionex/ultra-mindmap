"""\
MapReduce 引擎 — 移植自 Open-NotebookLM。
短文本走两阶段直生成（Analyze → Render），长文本走 MapReduce（Pre-Plan → Map → Collapse → Reduce）。
"""
from __future__ import annotations

import json
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

from langchain_text_splitters import RecursiveCharacterTextSplitter

from ..base import BaseEngine, Document, register_engine
from ...services.llm_service import generate_mindmap_text
from .prompts import (
    build_single_pass_prompt,
    build_analyze_structure_prompt,
    build_render_structure_prompt,
    build_pre_plan_prompt,
    build_map_prompt,
    build_collapse_prompt,
    build_reduce_prompt,
    build_merge_prompt,
    build_beautify_prompt,
)
from .utils import (
    count_tokens,
    get_chunk_token_limit,
    parse_json_safe,
    parse_map_json_safe,
    sanitize_nodes,
    clean_markdown_output,
    markdown_to_json,
    extract_md_headings,
    make_fallback_node,
    tokens_of_nodes,
    MAX_COLLAPSE_ITERATIONS,
)

log = logging.getLogger(__name__)


class MapReduceEngine(BaseEngine):
    name = "mapreduce"
    display_name = "MapReduce 生成"
    description = "先规划骨架，再分块提取概念，最后合并渲染。适合长篇论文、综述等复杂文档，生成质量更高。"

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
                "language": {
                    "type": "string",
                    "title": "输出语言",
                    "enum": ["zh", "en"],
                    "default": "zh",
                },
                "beautify": {
                    "type": "string",
                    "title": "美化输出",
                    "enum": ["否", "是"],
                    "default": "否",
                },
            },
        }

    def generate(self, documents: list[Document], params: dict) -> dict:
        model = params.get("model", "gpt-4o-mini")
        temperature = params.get("temperature", 0.3)
        max_depth = params.get("max_depth", 4)
        language = params.get("language", "zh")
        beautify = params.get("beautify", "否") == "是"

        def call_llm(prompt: str, temp: float | None = None) -> str:
            return generate_mindmap_text(prompt, model=model, temperature=temp if temp is not None else temperature)

        limit = get_chunk_token_limit(model)

        article_results = []
        for i, doc in enumerate(documents):
            tokens = count_tokens(doc.content, model)
            if tokens < limit:
                md = self._run_direct(doc, call_llm, language, max_depth)
            else:
                md = self._run_mapreduce(doc, i, call_llm, language, max_depth, limit, model)
            article_results.append({"filename": doc.title, "markdown": md})

        if len(article_results) == 1:
            final_md = article_results[0]["markdown"]
        else:
            final_md = self._merge_articles(article_results, call_llm, language, max_depth)

        if beautify:
            final_md = self._beautify(final_md, call_llm, language, max_depth)

        return markdown_to_json(final_md)

    def _run_direct(self, doc: Document, call_llm, language: str, max_depth: int) -> str:
        contents_str = f"=== {doc.title} ===\n{doc.content}\n\n"

        try:
            prompt = build_analyze_structure_prompt(contents_str, language, max_depth)
            structure = call_llm(prompt, 0.3).strip()
        except Exception as e:
            log.error(f"[Direct Analyze] {doc.title} 失败: {e}")
            structure = ""

        if not structure:
            prompt = build_single_pass_prompt(contents_str, language, max_depth)
            try:
                raw = call_llm(prompt, 0.3)
                return clean_markdown_output(raw)
            except Exception as e:
                log.error(f"[Direct Single] {doc.title} 失败: {e}")
                return f"# {doc.title}\n## Error\n### {e}"

        try:
            prompt = build_render_structure_prompt(structure, language, max_depth)
            raw = call_llm(prompt, 0.2)
            return clean_markdown_output(raw)
        except Exception as e:
            log.error(f"[Direct Render] {doc.title} 失败: {e}")
            return f"# {doc.title}\n## Error\n### {e}"

    def _run_mapreduce(
        self, doc: Document, file_idx: int, call_llm, language: str, max_depth: int, limit: int, model: str
    ) -> str:
        chunks = self._chunk_document(doc, file_idx, limit, model)
        log.info(f"[MapReduce {doc.title}] 分块 {len(chunks)} 个")

        # ---- Pre-Plan ----
        headings_md = extract_md_headings(doc.content) if doc.title.lower().endswith(".md") else ""
        head_chars = 12000
        tail_chars = 8000
        if len(doc.content) > head_chars + tail_chars + 500:
            excerpt = doc.content[:head_chars] + "\n\n[... 中间省略 ...]\n\n" + doc.content[-tail_chars:]
        else:
            excerpt = doc.content

        skeleton_json = ""
        try:
            prompt = build_pre_plan_prompt(headings_md, excerpt, language)
            raw = call_llm(prompt, 0.2)
            parsed = parse_json_safe(raw, "pre_plan")
            if isinstance(parsed, list) and parsed:
                skeleton_json = json.dumps(parsed, ensure_ascii=False, indent=2)
            log.info(f"[Pre-Plan {doc.title}] 骨架 {len(parsed) if isinstance(parsed, list) else '?'} 个主分支")
        except Exception as e:
            log.error(f"[Pre-Plan {doc.title}] 失败: {e}")

        # ---- Map (并发) ----
        map_results = self._map_phase(chunks, call_llm, language, skeleton_json)
        log.info(f"[Map {doc.title}] 完成，节点总数 {sum(len(r['nodes']) for r in map_results)}")

        # ---- Smart Collapse ----
        flat_nodes = []
        for mr in map_results:
            flat_nodes.extend(mr.get("nodes", []))
        flat_nodes = sanitize_nodes(flat_nodes)
        retained_nodes = self._smart_collapse(flat_nodes, limit, model, call_llm, language)
        retained_nodes = sanitize_nodes(retained_nodes)

        # ---- Reduce ----
        chunk_summaries = [
            {"chunk_id": mr.get("chunk_id", ""), "summary": mr.get("summary", "")}
            for mr in map_results
        ]
        reduce_nodes = [
            {
                "topic": n.get("topic", ""),
                "parent_topic": n.get("parent_topic", "ROOT"),
                "summary": n.get("summary", ""),
                "source_chunk_id": n.get("source_chunk_id", ""),
            }
            for n in retained_nodes
        ]
        reduce_nodes_json = json.dumps(reduce_nodes, ensure_ascii=False)

        red_head_chars = 25000
        red_tail_chars = 10000
        if len(doc.content) > red_head_chars + red_tail_chars + 500:
            reduce_excerpt = doc.content[:red_head_chars] + "\n\n[... 中间省略 ...]\n\n" + doc.content[-red_tail_chars:]
        else:
            reduce_excerpt = doc.content

        prompt = build_reduce_prompt(
            chunk_summaries=chunk_summaries,
            headings_md=headings_md,
            retained_nodes_json=reduce_nodes_json,
            language=language,
            max_depth=max_depth,
            skeleton_json=skeleton_json,
            source_excerpt=reduce_excerpt,
        )
        try:
            raw = call_llm(prompt, 0.3)
            return clean_markdown_output(raw)
        except Exception as e:
            log.error(f"[Reduce {doc.title}] 失败: {e}")
            return f"# {doc.title}\n## Error\n### {e}"

    def _chunk_document(self, doc: Document, file_idx: int, limit: int, model: str) -> list[dict]:
        tokens = count_tokens(doc.content, model)
        if tokens <= limit:
            return [{
                "chunk_id": f"file{file_idx}_chunk0",
                "source": doc.title,
                "text": doc.content,
                "token_count": tokens,
            }]
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=limit,
            chunk_overlap=200,
            length_function=lambda t: count_tokens(t, model),
            separators=["\n\n\n", "\n\n", "\n", "。", ".", "；", ";", " ", ""],
        )
        sub_texts = splitter.split_text(doc.content)
        return [
            {
                "chunk_id": f"file{file_idx}_chunk{j}",
                "source": doc.title,
                "text": sub,
                "token_count": count_tokens(sub, model),
            }
            for j, sub in enumerate(sub_texts)
        ]

    def _map_phase(self, chunks: list[dict], call_llm, language: str, skeleton_json: str) -> list[dict]:
        def process_chunk(chunk: dict) -> dict:
            prompt = build_map_prompt(chunk, language, skeleton_json=skeleton_json)
            try:
                raw = call_llm(prompt, 0.2)
                parsed = parse_map_json_safe(raw, chunk["chunk_id"])
            except Exception as e:
                log.error(f"[Map] chunk {chunk['chunk_id']} 失败: {e}")
                parsed = {"summary": "", "nodes": [make_fallback_node(chunk["chunk_id"], str(e))]}
            parsed["chunk_id"] = chunk["chunk_id"]
            return parsed

        results = []
        with ThreadPoolExecutor(max_workers=min(len(chunks), 8)) as executor:
            futures = {executor.submit(process_chunk, c): c["chunk_id"] for c in chunks}
            chunk_order = {c["chunk_id"]: i for i, c in enumerate(chunks)}
            result_map = {}
            for future in as_completed(futures):
                cid = futures[future]
                try:
                    result_map[cid] = future.result()
                except Exception as e:
                    log.error(f"[Map] chunk {cid} 异常: {e}")
                    result_map[cid] = {"chunk_id": cid, "summary": "", "nodes": [make_fallback_node(cid, str(e))]}
            for cid in sorted(result_map, key=lambda x: chunk_order.get(x, 0)):
                results.append(result_map[cid])
        return results

    def _smart_collapse(
        self, flat_nodes: list[dict], limit: int, model: str, call_llm, language: str
    ) -> list[dict]:
        nodes = list(flat_nodes)
        for round_num in range(MAX_COLLAPSE_ITERATIONS):
            cur_tokens = tokens_of_nodes(nodes, model)
            if cur_tokens <= limit:
                log.info(f"[Collapse] 已在阈值内 ({cur_tokens}/{limit})，停止")
                return nodes

            deficit = cur_tokens - limit
            avg = max(1, cur_tokens // max(len(nodes), 1))
            target_pair_size = max(2, int(limit / avg / 8))
            pair_span = max(2, target_pair_size) * 2
            pairs = []
            for i in range(0, len(nodes), pair_span):
                window = nodes[i:i + pair_span]
                if len(window) < 2:
                    continue
                mid = len(window) // 2
                pairs.append((window[:mid], window[mid:]))

            if not pairs:
                return nodes

            est = self._estimate_pairs_needed(pairs, deficit, model)
            candidates = pairs[:max(1, est)]
            log.info(f"[Collapse] 轮 {round_num + 1}: nodes={len(nodes)} tokens={cur_tokens}/{limit}")

            merged_results = []
            with ThreadPoolExecutor(max_workers=min(len(candidates), 4)) as executor:
                futures = []
                for a, b in candidates:
                    futures.append(executor.submit(self._merge_pair, a, b, call_llm, language))
                for future in futures:
                    try:
                        merged_results.append(future.result())
                    except Exception:
                        merged_results.append(None)

            next_nodes = []
            consumed_span = 0
            for i, merged in enumerate(merged_results):
                start = i * pair_span
                end = min(start + pair_span, len(nodes))
                if merged is None or not isinstance(merged, list):
                    next_nodes.extend(nodes[start:end])
                    consumed_span = end
                    continue
                tentative = next_nodes + list(merged) + nodes[end:]
                tentative_tokens = tokens_of_nodes(tentative, model)
                next_nodes.extend(merged)
                consumed_span = end
                if tentative_tokens <= limit:
                    next_nodes.extend(nodes[end:])
                    consumed_span = len(nodes)
                    break

            if consumed_span < len(nodes):
                next_nodes.extend(nodes[consumed_span:])

            nodes = next_nodes
        return nodes

    def _estimate_pairs_needed(self, pairs: list[tuple], deficit: int, model: str) -> int:
        if deficit <= 0 or not pairs:
            return 0
        cumulative_saved = 0
        for idx, (a, b) in enumerate(pairs, 1):
            pair_tokens = tokens_of_nodes(a + b, model)
            saved = int(pair_tokens * (1 / 3))
            cumulative_saved += saved
            if cumulative_saved >= deficit:
                return idx
        return len(pairs)

    def _merge_pair(self, a: list, b: list, call_llm, language: str) -> list:
        prompt = build_collapse_prompt(
            json.dumps(a, ensure_ascii=False),
            json.dumps(b, ensure_ascii=False),
            language,
        )
        try:
            raw = call_llm(prompt, 0.2)
            return parse_json_safe(raw, "collapse")
        except Exception as e:
            log.error(f"[Collapse] 合并失败: {e}")
            return a + b

    def _merge_articles(self, article_results: list[dict], call_llm, language: str, max_depth: int) -> str:
        prompt = build_merge_prompt(article_results, language, max_depth)
        try:
            raw = call_llm(prompt, 0.3)
            return clean_markdown_output(raw)
        except Exception as e:
            log.error(f"[Merge] 失败: {e}")
            return "# 综合思维导图\n\n" + "\n\n".join(
                "## " + p["filename"] + "\n" + (p.get("markdown") or "")
                for p in article_results
            )

    def _beautify(self, markdown: str, call_llm, language: str, max_depth: int) -> str:
        if not markdown.strip():
            return markdown
        prompt = build_beautify_prompt(markdown, language, max_depth)
        try:
            raw = call_llm(prompt, 0.3)
            polished = clean_markdown_output(raw)
            if polished.strip():
                return polished
        except Exception as e:
            log.error(f"[Beautify] 失败: {e}")
        return markdown


register_engine(MapReduceEngine())
