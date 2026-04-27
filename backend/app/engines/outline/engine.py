import re
from dataclasses import dataclass

from ..base import BaseEngine, Document, register_engine


ATX_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*#*\s*$")
SETEXT_RE = re.compile(r"^(=+|-+)\s*$")
NUMERIC_PREFIX_RE = re.compile(r"^(\d+(?:\.\d+)*)(?:[.)])?\s+(.+)$")
ROMAN_PREFIX_RE = re.compile(r"^([IVXLCDM]+)[.)]\s+(.+)$", re.IGNORECASE)
LETTER_PREFIX_RE = re.compile(r"^([A-Z])[.)]\s+(.+)$")
PLAIN_NUMBERED_RE = re.compile(
    r"^((?:\d+(?:\.\d+)*|[IVXLCDM]+|[A-Z])(?:[.)])?)\s+(.{3,140})$",
    re.IGNORECASE,
)

FRONT_BACK_TITLES = {
    "abstract",
    "acknowledgment",
    "acknowledgments",
    "references",
    "bibliography",
    "appendix",
}


@dataclass
class Heading:
    title: str
    marker_level: int
    line_no: int
    numbered_level: int | None = None


def _strip_inline_markup(text: str) -> str:
    text = re.sub(r"!\[[^\]]*\]\([^)]+\)", "", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"[*_`~]+", "", text)
    text = re.sub(r"<[^>]+>", "", text)
    return re.sub(r"\s+", " ", text).strip(" -\t")


def _numbered_level(title: str) -> int | None:
    clean = _strip_inline_markup(title)
    numeric = NUMERIC_PREFIX_RE.match(clean)
    if numeric:
        return len([p for p in numeric.group(1).split(".") if p])
    if ROMAN_PREFIX_RE.match(clean):
        return 1
    if LETTER_PREFIX_RE.match(clean):
        return 2
    if clean.lower() in FRONT_BACK_TITLES:
        return 1
    return None


def _looks_like_plain_heading(line: str) -> bool:
    if not PLAIN_NUMBERED_RE.match(line):
        return False
    if line.endswith((".", ",", ";", ":")) and len(line.split()) > 12:
        return False
    return True


def extract_headings(content: str, include_plain_numbered: bool = True) -> list[Heading]:
    markdown_headings: list[Heading] = []
    plain_headings: list[Heading] = []
    lines = content.splitlines()
    in_fence = False

    for idx, raw_line in enumerate(lines):
        line = raw_line.strip()
        if line.startswith("```") or line.startswith("~~~"):
            in_fence = not in_fence
            continue
        if in_fence or not line:
            continue

        atx = ATX_HEADING_RE.match(line)
        if atx:
            title = _strip_inline_markup(atx.group(2))
            if title:
                markdown_headings.append(
                    Heading(
                        title=title,
                        marker_level=len(atx.group(1)),
                        line_no=idx + 1,
                        numbered_level=_numbered_level(title),
                    )
                )
            continue

        if idx + 1 < len(lines) and SETEXT_RE.match(lines[idx + 1].strip()):
            title = _strip_inline_markup(line)
            if title and not title.startswith("|"):
                marker_level = 1 if lines[idx + 1].strip().startswith("=") else 2
                markdown_headings.append(
                    Heading(
                        title=title,
                        marker_level=marker_level,
                        line_no=idx + 1,
                        numbered_level=_numbered_level(title),
                    )
                )
            continue

        if include_plain_numbered and _looks_like_plain_heading(line):
            title = _strip_inline_markup(line)
            numbered_level = _numbered_level(title)
            if numbered_level is not None:
                plain_headings.append(
                    Heading(
                        title=title,
                        marker_level=numbered_level,
                        line_no=idx + 1,
                        numbered_level=numbered_level,
                    )
                )

    if len(markdown_headings) >= 2:
        return markdown_headings
    return sorted(markdown_headings + plain_headings, key=lambda h: h.line_no)


def _resolve_levels(headings: list[Heading], max_depth: int) -> list[tuple[int, str]]:
    marker_levels = {h.marker_level for h in headings}
    flat_markdown = len(marker_levels) == 1
    resolved: list[tuple[int, str]] = []

    for heading in headings:
        if heading.numbered_level is not None:
            level = heading.numbered_level
        elif flat_markdown and resolved:
            previous_level = resolved[-1][0]
            previous_numbered = headings[len(resolved) - 1].numbered_level is not None
            level = previous_level + 1 if previous_numbered else previous_level
        else:
            level = heading.marker_level

        resolved.append((max(1, min(level, max_depth)), heading.title))

    return resolved


def build_outline_tree(title: str, content: str, max_depth: int = 10) -> dict:
    headings = extract_headings(content)
    if not headings:
        return {"name": title, "children": [{"name": "未检测到标题层级", "children": []}]}

    root = {"name": title, "children": []}
    stack: list[tuple[int, dict]] = [(0, root)]

    for level, heading_title in _resolve_levels(headings, max_depth=max_depth):
        node = {"name": heading_title, "children": []}
        while stack and stack[-1][0] >= level:
            stack.pop()
        stack[-1][1]["children"].append(node)
        stack.append((level, node))

    return root


class OutlineEngine(BaseEngine):
    name = "outline"
    display_name = "标题层级树"
    description = "按文档标题模式自动检测层级，不调用 LLM，直接生成结构化思维导图。"

    def get_params_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "max_depth": {
                    "type": "integer",
                    "title": "最大深度",
                    "default": 10,
                },
            },
        }

    def generate(self, documents: list[Document], params: dict) -> dict:
        max_depth = int(params.get("max_depth", 10))
        trees = [build_outline_tree(doc.title, doc.content, max_depth=max_depth) for doc in documents]
        if len(trees) == 1:
            return trees[0]
        return {"name": "文档层级树", "children": trees}


register_engine(OutlineEngine())
