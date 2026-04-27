import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from render_bench_report import build_html, render_markdown_to_html  # noqa: E402


def test_render_markdown_to_html_handles_headings_lists_and_code():
    html = render_markdown_to_html(
        "# Title\n\n- item a\n- item b\n\n1. step one\n\n```py\nprint('x')\n```"
    )

    assert "<h1>Title</h1>" in html
    assert "<ul><li>item a</li><li>item b</li></ul>" in html
    assert "<ol><li>step one</li></ol>" in html
    assert "<pre><code>print('x')</code></pre>" in html


def test_build_html_includes_summary_and_task_content():
    payload = {
        "config": {
            "engine_a": "direct",
            "engine_b": "docmerge",
            "judge_model": "gpt-5.4",
            "group_size": 2,
            "dataset_size": 2,
            "task_count": 1,
            "sample_count": 1,
            "seed": 42,
        },
        "summary": {
            "task_count": 1,
            "pair_size": 2,
            "wins_a": 0,
            "wins_b": 1,
            "ties": 0,
            "avg_total_a": 19.0,
            "avg_total_b": 22.0,
            "avg_elapsed_s": 90.0,
        },
        "tasks": [
            {
                "filename": "doc-a +1",
                "filenames": ["doc-a.md", "doc-b.md"],
                "engine_a": "direct",
                "engine_b": "docmerge",
                "score_a": {
                    "coverage": 3,
                    "hierarchy": 4,
                    "balance": 4,
                    "conciseness": 5,
                    "accuracy": 3,
                    "rationale": "## A\n\n- brief",
                },
                "score_b": {
                    "coverage": 5,
                    "hierarchy": 5,
                    "balance": 4,
                    "conciseness": 4,
                    "accuracy": 4,
                    "rationale": "Better structure",
                },
                "elapsed_s": 90.0,
            }
        ],
    }

    html = build_html(payload, "bench.json")

    assert "Bench Report" in html
    assert "doc-a.md + doc-b.md" in html
    assert "19" in html
    assert "22" in html
    assert "<h2>A</h2>" in html
    assert "Better structure" in html
