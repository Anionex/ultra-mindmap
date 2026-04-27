from app.engines.base import Document
from app.engines.outline.engine import OutlineEngine, build_outline_tree


def child_names(node):
    return [child["name"] for child in node["children"]]


def test_markdown_heading_levels_build_tree():
    tree = build_outline_tree(
        "sample.md",
        """# Title

## Part A
### Detail A1
## Part B
""",
    )

    assert tree["name"] == "sample.md"
    assert child_names(tree) == ["Title"]
    assert child_names(tree["children"][0]) == ["Part A", "Part B"]
    assert child_names(tree["children"][0]["children"][0]) == ["Detail A1"]


def test_flat_markdown_headings_infer_numbered_levels():
    tree = build_outline_tree(
        "paper.md",
        """# Paper Title

# 1 INTRODUCTION
# 1.1 Motivation
# 1.1.1 Scope
# 2 RELATED WORK
# A. Contribution
""",
    )

    assert child_names(tree) == ["Paper Title", "1 INTRODUCTION", "2 RELATED WORK"]
    intro = tree["children"][1]
    assert child_names(intro) == ["1.1 Motivation"]
    assert child_names(intro["children"][0]) == ["1.1.1 Scope"]
    related = tree["children"][2]
    assert child_names(related) == ["A. Contribution"]


def test_outline_engine_multi_document_root():
    result = OutlineEngine().generate(
        [
            Document(title="a.md", content="# A\n## A1"),
            Document(title="b.md", content="# B\n## B1"),
        ],
        {"max_depth": 6},
    )

    assert result["name"] == "文档层级树"
    assert child_names(result) == ["a.md", "b.md"]


def test_no_headings_returns_fallback_node():
    tree = build_outline_tree("plain.txt", "only a paragraph")

    assert tree == {
        "name": "plain.txt",
        "children": [{"name": "未检测到标题层级", "children": []}],
    }
