from app.services.mindmap_format import extract_markdown, extract_tree, normalize_mindmap_payload


def test_extract_tree_supports_markdown():
    tree = extract_tree("# Root\n## Child\n### Leaf")

    assert tree == {
        "name": "Root",
        "children": [
            {
                "name": "Child",
                "children": [{"name": "Leaf", "children": []}],
            }
        ],
    }


def test_extract_tree_supports_json_string():
    tree = extract_tree('{"name":"Root","children":[{"name":"Child","children":[]}]}')

    assert tree == {
        "name": "Root",
        "children": [{"name": "Child", "children": []}],
    }


def test_normalize_payload_adds_markdown_for_legacy_tree():
    payload = normalize_mindmap_payload(
        {"name": "Root", "children": [{"name": "Child", "children": []}]}
    )

    assert payload == {
        "name": "Root",
        "children": [{"name": "Child", "children": []}],
        "markdown": "# Root\n## Child",
    }


def test_extract_markdown_supports_legacy_json_wrapper():
    markdown = extract_markdown({"markdown": "# Root\n## Child"})

    assert markdown == "# Root\n## Child"
