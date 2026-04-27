from app.engines.chunked.engine import ChunkedEngine
from app.engines.direct.engine import DirectEngine
from app.engines.docmerge.engine import DocMergeEngine
from app.engines.outline.engine import OutlineEngine, build_outline_tree


def test_llm_engines_default_max_depth_is_ten():
    assert DirectEngine().get_params_schema()["properties"]["max_depth"]["default"] == 10
    assert ChunkedEngine().get_params_schema()["properties"]["max_depth"]["default"] == 10
    assert DocMergeEngine().get_params_schema()["properties"]["max_depth"]["default"] == 10


def test_outline_engine_default_max_depth_is_ten():
    assert OutlineEngine().get_params_schema()["properties"]["max_depth"]["default"] == 10


def test_build_outline_tree_defaults_to_ten_levels():
    content = "\n".join(
        [
            "1 Level 1",
            "1.1 Level 2",
            "1.1.1 Level 3",
            "1.1.1.1 Level 4",
            "1.1.1.1.1 Level 5",
            "1.1.1.1.1.1 Level 6",
            "1.1.1.1.1.1.1 Level 7",
            "1.1.1.1.1.1.1.1 Level 8",
            "1.1.1.1.1.1.1.1.1 Level 9",
            "1.1.1.1.1.1.1.1.1.1 Level 10",
            "1.1.1.1.1.1.1.1.1.1.1 Level 11",
        ]
    )

    tree = build_outline_tree("deep.md", content)

    def deepest_depth(node: dict, depth: int = 0) -> int:
        if not node["children"]:
            return depth
        return max(deepest_depth(child, depth + 1) for child in node["children"])

    assert deepest_depth(tree) == 10
