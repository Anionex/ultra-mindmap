from app.engines.base import Document
from app.engines.docmerge.engine import DocMergeEngine


def test_docmerge_calls_llm_once_per_document_then_once_for_merge(monkeypatch):
    calls = []

    def fake_generate_mindmap_json(prompt, model, temperature):
        calls.append(
            {
                "prompt": prompt,
                "model": model,
                "temperature": temperature,
            }
        )
        if "请把下面多篇文档各自生成的思维导图合并为一个最终思维导图" in prompt:
            return {"name": "merged", "children": [{"name": "shared", "children": []}]}
        if "=== 文档: doc-a ===" in prompt:
            return {"name": "doc-a", "children": [{"name": "topic-a", "children": []}]}
        if "=== 文档: doc-b ===" in prompt:
            return {"name": "doc-b", "children": [{"name": "topic-b", "children": []}]}
        raise AssertionError("unexpected prompt")

    monkeypatch.setattr("app.engines.docmerge.engine.generate_mindmap_json", fake_generate_mindmap_json)

    result = DocMergeEngine().generate(
        [
            Document(title="doc-a", content="alpha"),
            Document(title="doc-b", content="beta"),
        ],
        {"model": "test-model", "temperature": 0.2, "max_depth": 5},
    )

    assert result == {"name": "merged", "children": [{"name": "shared", "children": []}]}
    assert len(calls) == 3
    assert "当前只处理这一篇文档" in calls[0]["prompt"]
    assert "当前只处理这一篇文档" in calls[1]["prompt"]
    assert "请把下面多篇文档各自生成的思维导图合并为一个最终思维导图" in calls[2]["prompt"]
    assert "\"name\": \"doc-a\"" in calls[2]["prompt"]
    assert "\"name\": \"doc-b\"" in calls[2]["prompt"]


def test_docmerge_single_document_returns_single_tree_without_merge(monkeypatch):
    calls = []

    def fake_generate_mindmap_json(prompt, model, temperature):
        calls.append(prompt)
        return {"name": "doc-a", "children": [{"name": "topic-a", "children": []}]}

    monkeypatch.setattr("app.engines.docmerge.engine.generate_mindmap_json", fake_generate_mindmap_json)

    result = DocMergeEngine().generate(
        [Document(title="doc-a", content="alpha")],
        {"model": "test-model", "temperature": 0.2, "max_depth": 5},
    )

    assert result == {"name": "doc-a", "children": [{"name": "topic-a", "children": []}]}
    assert len(calls) == 1
