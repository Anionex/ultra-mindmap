"""\
MapReduce 引擎的工具函数。
"""
from __future__ import annotations

import json
import re
from typing import List

import tiktoken

_encoding_cache: dict[str, tiktoken.Encoding] = {}

_MODEL_CONTEXT_WINDOWS = {
    "gpt-4": 8192,
    "gpt-4-turbo": 128000,
    "gpt-4o": 128000,
    "gpt-4o-mini": 128000,
    "gpt-4.1": 1048576,
    "gpt-4.1-mini": 1048576,
    "gpt-4.1-nano": 1048576,
    "o3": 200000,
    "o3-mini": 200000,
    "o4-mini": 200000,
    "deepseek-v3": 64000,
    "deepseek-chat": 64000,
    "deepseek-reasoner": 64000,
    "claude-sonnet-4-20250514": 200000,
    "claude-opus-4-20250514": 200000,
    "gemini-2.5-flash": 1048576,
    "gemini-2.5-pro": 1048576,
}
DEFAULT_CONTEXT_WINDOW = 64000
LONG_TEXT_THRESHOLD_RATIO = 0.6
MAX_COLLAPSE_ITERATIONS = 5


def _get_encoding(model: str = "") -> tiktoken.Encoding:
    key = model or "_default_"
    if key not in _encoding_cache:
        try:
            _encoding_cache[key] = tiktoken.encoding_for_model(model)
        except (KeyError, Exception):
            _encoding_cache[key] = tiktoken.get_encoding("cl100k_base")
    return _encoding_cache[key]


def count_tokens(text: str, model: str = "") -> int:
    try:
        return len(_get_encoding(model).encode(text))
    except Exception:
        return len(text) // 3


def get_context_window(model: str) -> int:
    model_lower = model.lower() if model else ""
    best_key, best_val = "", DEFAULT_CONTEXT_WINDOW
    for key, val in _MODEL_CONTEXT_WINDOWS.items():
        if key in model_lower and len(key) > len(best_key):
            best_key, best_val = key, val
    return best_val


def get_chunk_token_limit(model: str) -> int:
    return int(get_context_window(model) * LONG_TEXT_THRESHOLD_RATIO)


# ==================== JSON 安全解析 ====================

def strip_code_fences(text: str) -> str:
    t = text.strip()
    if t.startswith("```"):
        lines = t.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        t = "\n".join(lines).strip()
    return t


def make_fallback_node(chunk_id: str, summary: str) -> dict:
    return {
        "node_id": f"{chunk_id}_fallback",
        "topic": f"Content from {chunk_id}",
        "parent_topic": "ROOT",
        "summary": summary,
        "importance_score": 3,
        "source_chunk_id": chunk_id,
    }


def parse_json_safe(raw_text: str, chunk_id: str) -> list:
    if not raw_text or not raw_text.strip():
        return [make_fallback_node(chunk_id, "Empty response")]
    text = strip_code_fences(raw_text)
    try:
        result = json.loads(text)
        if isinstance(result, list):
            return result
        if isinstance(result, dict) and isinstance(result.get("nodes"), list):
            return result["nodes"]
    except json.JSONDecodeError:
        pass
    match = re.search(r'\[[\s\S]*\]', text)
    if match:
        try:
            result = json.loads(match.group())
            if isinstance(result, list):
                return result
        except json.JSONDecodeError:
            pass
    return [make_fallback_node(chunk_id, raw_text[:500])]


def parse_map_json_safe(raw_text: str, chunk_id: str) -> dict:
    empty_fallback = {"summary": "", "nodes": [make_fallback_node(chunk_id, "Empty response")]}
    if not raw_text or not raw_text.strip():
        return empty_fallback
    text = strip_code_fences(raw_text)
    try:
        result = json.loads(text)
        if isinstance(result, dict):
            nodes = result.get("nodes") or []
            if not isinstance(nodes, list):
                nodes = []
            if not nodes:
                nodes = [make_fallback_node(chunk_id, "Empty nodes")]
            return {"summary": str(result.get("summary", "")).strip(), "nodes": nodes}
        if isinstance(result, list):
            return {"summary": "", "nodes": result or [make_fallback_node(chunk_id, "Empty list")]}
    except json.JSONDecodeError:
        pass
    match = re.search(r'\[[\s\S]*\]', text)
    if match:
        try:
            nodes = json.loads(match.group())
            if isinstance(nodes, list) and nodes:
                return {"summary": "", "nodes": nodes}
        except json.JSONDecodeError:
            pass
    return {"summary": "", "nodes": [make_fallback_node(chunk_id, raw_text[:500])]}


# ==================== 节点净化 ====================

_BAD_TOPIC_PATTERNS = [
    re.compile(r"^\s*\d{4}\s*年?\s*$"),
    re.compile(r"^\s*\d+(\.\d+)?\s*%\s*$"),
    re.compile(r"^\s*\d+(\.\d+)?\s*(倍|次|篇|个|项|章|节|页|卷|期)\s*$"),
    re.compile(r"^\s*\d+\s*[xX×]\s*\d+\s*$"),
    re.compile(r"^\s*\d+\s*[-–:：]\s*\d+\s*$"),
    re.compile(r"^[\s\d\.,\-:：%年月日]+$"),
]

_BAD_TOPIC_KEYWORDS = {
    "引言", "简介", "概述", "背景", "研究背景", "文章结构", "章节概览", "章节安排",
    "致谢", "参考文献", "附录", "索引", "图表目录",
    "研究方法", "研究内容", "主要内容", "主要贡献", "论文组织", "论文结构",
}


def _is_bad_topic(topic: str) -> bool:
    if not topic or not topic.strip():
        return True
    t = topic.strip()
    for pat in _BAD_TOPIC_PATTERNS:
        if pat.match(t):
            return True
    return t in _BAD_TOPIC_KEYWORDS


def sanitize_nodes(nodes: List[dict]) -> List[dict]:
    if not nodes:
        return nodes
    topic_to_idx = {n.get("topic", "").strip(): i for i, n in enumerate(nodes)}
    good: List[dict] = []
    for n in nodes:
        topic = str(n.get("topic", "")).strip()
        if _is_bad_topic(topic):
            parent = str(n.get("parent_topic", "")).strip()
            if parent and parent != "ROOT" and parent in topic_to_idx:
                pidx = topic_to_idx[parent]
                if pidx < len(nodes):
                    parent_node = nodes[pidx]
                    extra = n.get("summary", "") or topic
                    if extra:
                        cur = str(parent_node.get("summary", "")).strip()
                        parent_node["summary"] = (cur + (" " if cur else "") + str(extra)).strip()
            continue
        good.append(n)
    return good


# ==================== Markdown 输出清洗 ====================

def clean_markdown_output(raw: str) -> str:
    if not raw:
        return "# Error\n## Generation failed"
    if "```" in raw:
        lines = raw.split("\n")
        in_code_block = False
        code_lines = []
        for line in lines:
            if line.strip().startswith("```"):
                in_code_block = not in_code_block
                continue
            if in_code_block:
                code_lines.append(line)
        if code_lines:
            return "\n".join(code_lines)
    return raw


# ==================== Markdown Heading Tree → JSON ====================

_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+)")


def markdown_to_json(markdown: str) -> dict:
    """将 Markdown 标题树转换为 {name, children} 格式的 JSON。"""
    if not markdown or not markdown.strip():
        return {"name": "思维导图", "children": []}

    stack: list[tuple[int, dict]] = []
    root = {"name": "思维导图", "children": []}
    stack.append((0, root))

    for line in markdown.split("\n"):
        m = _HEADING_RE.match(line)
        if not m:
            continue
        depth = len(m.group(1))
        text = m.group(2).strip()
        node = {"name": text, "children": []}

        if depth == 1:
            root["name"] = text
            stack = [(0, root)]
            continue

        while len(stack) > 1 and stack[-1][0] >= depth:
            stack.pop()

        stack[-1][1]["children"].append(node)
        stack.append((depth, node))

    _prune_empty_children(root)
    return root


def _prune_empty_children(node: dict):
    for child in node.get("children", []):
        _prune_empty_children(child)
    if not node.get("children"):
        node.pop("children", None)


def extract_md_headings(content: str, max_level: int = 3) -> str:
    if not content:
        return ""
    lines = []
    for line in content.split("\n"):
        m = _HEADING_RE.match(line)
        if not m:
            continue
        depth = len(m.group(1))
        if depth > max_level:
            continue
        lines.append(f"{'#' * depth} {m.group(2).strip()}")
    return "\n".join(lines)


def tokens_of_nodes(nodes: list[dict], model: str) -> int:
    return count_tokens(json.dumps(nodes, ensure_ascii=False), model)
