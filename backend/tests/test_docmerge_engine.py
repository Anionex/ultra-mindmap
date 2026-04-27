from app.engines.base import Document
from app.engines.docmerge.engine import DocMergeEngine


def test_docmerge_calls_llm_once_per_document_then_once_for_merge(monkeypatch):
    calls = []

    def fake_generate_mindmap_markdown(prompt, model, temperature):
        calls.append(
            {
                "prompt": prompt,
                "model": model,
                "temperature": temperature,
            }
        )
        if "已有的文档思维导图如下" in prompt:
            return "# merged\n## shared"
        if "=== 文档: doc-a ===" in prompt:
            return "# doc-a\n## topic-a"
        if "=== 文档: doc-b ===" in prompt:
            return "# doc-b\n## topic-b"
        raise AssertionError("unexpected prompt")

    monkeypatch.setattr("app.engines.docmerge.engine.generate_mindmap_markdown", fake_generate_mindmap_markdown)

    result = DocMergeEngine().generate(
        [
            Document(title="doc-a", content="alpha"),
            Document(title="doc-b", content="beta"),
        ],
        {"model": "test-model", "temperature": 0.2, "max_depth": 5},
    )

    assert result == {
        "name": "merged",
        "children": [{"name": "shared", "children": []}],
        "markdown": "# merged\n## shared",
    }
    assert len(calls) == 3
    assert "直接输出 Markdown 标题层级" in calls[0]["prompt"]
    assert "=== 文档: doc-a ===" in calls[0]["prompt"]
    assert "直接输出 Markdown 标题层级" in calls[1]["prompt"]
    assert "=== 文档: doc-b ===" in calls[1]["prompt"]
    assert "先分析关系再组织结构" in calls[2]["prompt"]
    assert "不强行统一抽象" in calls[2]["prompt"]
    assert "=== 文档思维导图: doc-a ===" in calls[2]["prompt"]
    assert "# doc-a\n## topic-a" in calls[2]["prompt"]
    assert "=== 文档思维导图: doc-b ===" in calls[2]["prompt"]
    assert "# doc-b\n## topic-b" in calls[2]["prompt"]


def test_docmerge_single_document_returns_single_tree_without_merge(monkeypatch):
    calls = []

    def fake_generate_mindmap_markdown(prompt, model, temperature):
        calls.append(prompt)
        return "# doc-a\n## topic-a"

    monkeypatch.setattr("app.engines.docmerge.engine.generate_mindmap_markdown", fake_generate_mindmap_markdown)

    result = DocMergeEngine().generate(
        [Document(title="doc-a", content="alpha")],
        {"model": "test-model", "temperature": 0.2, "max_depth": 5},
    )

    assert result == {
        "name": "doc-a",
        "children": [{"name": "topic-a", "children": []}],
        "markdown": "# doc-a\n## topic-a",
    }
    assert len(calls) == 1
