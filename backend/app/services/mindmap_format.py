import json
import re


HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")


def _clean_label(value: str | None) -> str:
    text = (value or "").strip()
    return re.sub(r"\s+", " ", text)


def normalize_tree(node: dict | None, fallback_root: str = "思维导图") -> dict:
    if not isinstance(node, dict):
        return {"name": fallback_root, "children": []}

    name = _clean_label(node.get("name")) or fallback_root
    children = [
        normalize_tree(child, fallback_root=fallback_root)
        for child in node.get("children", [])
        if isinstance(child, dict)
    ]
    return {"name": name, "children": children}


def tree_to_markdown(node: dict | None, depth: int = 1) -> str:
    tree = normalize_tree(node)
    lines = [f"{'#' * depth} {tree['name']}"]
    for child in tree["children"]:
        child_markdown = tree_to_markdown(child, depth + 1).strip()
        if child_markdown:
            lines.append(child_markdown)
    return "\n".join(lines)


def markdown_to_tree(markdown: str, fallback_root: str = "思维导图") -> dict:
    lines = (markdown or "").splitlines()
    root = {"name": fallback_root, "children": []}
    stack: list[tuple[int, dict]] = [(0, root)]

    for raw_line in lines:
        line = raw_line.strip()
        if not line:
            continue
        match = HEADING_RE.match(line)
        if not match:
            continue

        level = len(match.group(1))
        node = {"name": _clean_label(match.group(2)), "children": []}
        while stack and stack[-1][0] >= level:
            stack.pop()
        stack[-1][1]["children"].append(node)
        stack.append((level, node))

    if not root["children"]:
        return {"name": fallback_root, "children": []}
    if len(root["children"]) == 1:
        return root["children"][0]
    return root


def _coerce_payload(payload: str | dict | None) -> str | dict | None:
    if not isinstance(payload, str):
        return payload
    text = payload.strip()
    if not text:
        return ""
    if text.startswith("{"):
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return text
    return text


def extract_tree(payload: str | dict | None, fallback_root: str = "思维导图") -> dict:
    payload = _coerce_payload(payload)
    if isinstance(payload, str):
        return markdown_to_tree(payload, fallback_root=fallback_root)
    if not isinstance(payload, dict):
        return {"name": fallback_root, "children": []}
    if isinstance(payload.get("tree"), dict):
        return normalize_tree(payload["tree"], fallback_root=fallback_root)
    if "name" in payload:
        return normalize_tree(payload, fallback_root=fallback_root)
    if isinstance(payload.get("markdown"), str):
        return markdown_to_tree(payload["markdown"], fallback_root=fallback_root)
    return {"name": fallback_root, "children": []}


def extract_markdown(payload: str | dict | None, fallback_root: str = "思维导图") -> str:
    payload = _coerce_payload(payload)
    if isinstance(payload, str):
        return payload.strip()
    if isinstance(payload, dict):
        markdown = (payload.get("markdown") or "").strip()
        if markdown:
            return markdown
    return tree_to_markdown(extract_tree(payload, fallback_root=fallback_root))


def build_mindmap_response(
    tree: dict | None = None,
    markdown: str | None = None,
    fallback_root: str = "思维导图",
) -> dict:
    normalized_tree = normalize_tree(tree, fallback_root=fallback_root) if tree else markdown_to_tree(markdown or "", fallback_root=fallback_root)
    normalized_markdown = (markdown or "").strip() or tree_to_markdown(normalized_tree)
    return {
        "name": normalized_tree["name"],
        "children": normalized_tree["children"],
        "markdown": normalized_markdown,
    }


def normalize_mindmap_payload(payload: str | dict | None, fallback_root: str = "思维导图") -> dict:
    return build_mindmap_response(
        tree=extract_tree(payload, fallback_root=fallback_root),
        markdown=extract_markdown(payload, fallback_root=fallback_root),
        fallback_root=fallback_root,
    )
