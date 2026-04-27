import argparse
import html
import json
import math
import re
from pathlib import Path
from urllib.parse import urlparse


DIMENSIONS = ["coverage", "hierarchy", "balance", "conciseness", "accuracy"]
DIMENSION_LABELS = {
    "coverage": "Coverage",
    "hierarchy": "Hierarchy",
    "balance": "Balance",
    "conciseness": "Conciseness",
    "accuracy": "Accuracy",
}


def escape_html(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _looks_like_external_url(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https", "data", "file"}


def resolve_asset_url(url: str, asset_root: Path | None) -> str:
    if not url:
        return url
    stripped = url.strip()
    if stripped.startswith("#") or stripped.startswith("/") or _looks_like_external_url(stripped):
        return stripped
    if asset_root is None:
        return stripped
    return Path(asset_root, stripped).resolve().as_uri()


def rewrite_markdown_asset_urls(content: str, asset_root: Path | None) -> str:
    def replace_image(match: re.Match) -> str:
        alt, src = match.group(1), match.group(2)
        return f"![{alt}]({resolve_asset_url(src, asset_root)})"

    def replace_link(match: re.Match) -> str:
        label, href = match.group(1), match.group(2)
        return f"[{label}]({resolve_asset_url(href, asset_root)})"

    content = re.sub(r"!\[([^\]]*)\]\(([^)]+)\)", replace_image, content)
    content = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", replace_link, content)
    return content


def rewrite_html_asset_urls(raw_html: str, asset_root: Path | None) -> str:
    def replace_attr(match: re.Match) -> str:
        attr = match.group(1)
        quote = match.group(2)
        value = match.group(3)
        resolved = html.escape(resolve_asset_url(value, asset_root), quote=True)
        return f"{attr}={quote}{resolved}{quote}"

    return re.sub(r'(src|href)=(["\'])(.+?)\2', replace_attr, raw_html, flags=re.IGNORECASE)


def is_probable_raw_html(line: str) -> bool:
    stripped = line.strip().lower()
    prefixes = (
        "<table", "</table", "<thead", "</thead", "<tbody", "</tbody", "<tr", "</tr",
        "<td", "</td", "<th", "</th", "<img", "<figure", "</figure", "<figcaption",
        "</figcaption", "<div", "</div", "<span", "</span", "<p", "</p", "<svg", "</svg",
    )
    return stripped.startswith(prefixes)


def render_inline(text: str) -> str:
    rendered = escape_html(text)
    rendered = re.sub(
        r"!\[([^\]]*)\]\(([^)]+)\)",
        lambda m: f'<img src="{html.escape(m.group(2), quote=True)}" alt="{html.escape(m.group(1), quote=True)}" class="md-image" />',
        rendered,
    )
    rendered = re.sub(r"`([^`]+)`", r'<code class="inline-code">\1</code>', rendered)
    rendered = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", rendered)
    rendered = re.sub(r"(^|[^*])\*([^*]+)\*", r"\1<em>\2</em>", rendered)
    rendered = re.sub(
        r"\[([^\]]+)\]\(([^)]+)\)",
        r'<a href="\2" target="_blank" rel="noreferrer">\1</a>',
        rendered,
    )
    return rendered


def render_markdown_to_html(content: str, asset_root: Path | None = None) -> str:
    if not content:
        return ""
    content = rewrite_markdown_asset_urls(content, asset_root)

    code_block_re = re.compile(r"```([a-zA-Z0-9_-]+)?\n([\s\S]*?)```")
    html_parts: list[str] = []
    last_index = 0

    def process_text_block(block: str) -> str:
        lines = block.split("\n")
        block_parts: list[str] = []
        in_ul = False
        in_ol = False

        def close_lists() -> None:
            nonlocal in_ul, in_ol
            if in_ul:
                block_parts.append("</ul>")
                in_ul = False
            if in_ol:
                block_parts.append("</ol>")
                in_ol = False

        for line in lines:
            trimmed = line.strip()
            if is_probable_raw_html(line):
                close_lists()
                block_parts.append(rewrite_html_asset_urls(line, asset_root))
                continue

            heading_match = re.match(r"^(#{1,6})\s+(.+)$", trimmed)
            if heading_match:
                close_lists()
                level = len(heading_match.group(1))
                block_parts.append(f"<h{level}>{render_inline(heading_match.group(2))}</h{level}>")
                continue

            if re.match(r"^[-*]\s+", trimmed):
                if not in_ul:
                    close_lists()
                    block_parts.append("<ul>")
                    in_ul = True
                item_text = re.sub(r"^[-*]\s+", "", trimmed)
                block_parts.append(f"<li>{render_inline(item_text)}</li>")
                continue

            if re.match(r"^\d+\.\s+", trimmed):
                if not in_ol:
                    close_lists()
                    block_parts.append("<ol>")
                    in_ol = True
                item_text = re.sub(r"^\d+\.\s+", "", trimmed)
                block_parts.append(f"<li>{render_inline(item_text)}</li>")
                continue

            if not trimmed:
                close_lists()
                block_parts.append('<div class="spacer"></div>')
                continue

            close_lists()
            block_parts.append(f"<p>{render_inline(line)}</p>")

        close_lists()
        return "".join(block_parts)

    for match in code_block_re.finditer(content):
        html_parts.append(process_text_block(content[last_index:match.start()]))
        html_parts.append(f"<pre><code>{escape_html(match.group(2).rstrip())}</code></pre>")
        last_index = match.end()

    html_parts.append(process_text_block(content[last_index:]))
    return "".join(html_parts)


def score_total(score: dict) -> int:
    return sum(int(score[key]) for key in DIMENSIONS)


def mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def pstdev(values: list[float]) -> float:
    if not values:
        return 0.0
    mu = mean(values)
    return math.sqrt(sum((value - mu) ** 2 for value in values) / len(values))


def short_label(task: dict) -> str:
    filenames = task.get("filenames") or [task.get("filename", "")]
    label = " + ".join(filenames)
    return label if len(label) <= 56 else label[:53] + "..."


def generator_label(config: dict) -> str:
    params_a = config.get("params_a") or {}
    params_b = config.get("params_b") or {}
    model_a = params_a.get("model")
    model_b = params_b.get("model")
    if model_a and model_b and model_a != model_b:
        return f"{model_a} / {model_b}"
    if model_a:
        return str(model_a)
    if model_b:
        return str(model_b)
    return "unknown"


def prepare_report_data(payload: dict, source_name: str, asset_root: Path | None = None) -> dict:
    config = payload.get("config", {})
    summary = payload.get("summary", {})
    tasks = payload.get("tasks", [])

    means_a = [round(mean([int(task["score_a"][dim]) for task in tasks]), 2) for dim in DIMENSIONS] if tasks else [0] * len(DIMENSIONS)
    means_b = [round(mean([int(task["score_b"][dim]) for task in tasks]), 2) for dim in DIMENSIONS] if tasks else [0] * len(DIMENSIONS)
    std_a = [round(pstdev([int(task["score_a"][dim]) for task in tasks]), 2) for dim in DIMENSIONS] if tasks else [0] * len(DIMENSIONS)
    std_b = [round(pstdev([int(task["score_b"][dim]) for task in tasks]), 2) for dim in DIMENSIONS] if tasks else [0] * len(DIMENSIONS)

    wins = []
    for dim in DIMENSIONS:
        a_wins = 0
        b_wins = 0
        ties = 0
        for task in tasks:
            a = int(task["score_a"][dim])
            b = int(task["score_b"][dim])
            if a > b:
                a_wins += 1
            elif b > a:
                b_wins += 1
            else:
                ties += 1
        wins.append([a_wins, b_wins, ties])

    per_task = []
    for task in tasks:
        total_a = score_total(task["score_a"])
        total_b = score_total(task["score_b"])
        filenames = task.get("filenames") or [task.get("filename", "")]
        per_task.append(
            {
                "label": short_label(task),
                "title": " + ".join(filenames),
                "filenames": filenames,
                "delta": total_a - total_b,
                "a": total_a,
                "b": total_b,
                "score_a": task["score_a"],
                "score_b": task["score_b"],
                "mindmap_a": task.get("mindmap_a", ""),
                "mindmap_b": task.get("mindmap_b", ""),
                "rationale_a_html": render_markdown_to_html(task["score_a"].get("rationale", ""), asset_root=asset_root),
                "rationale_b_html": render_markdown_to_html(task["score_b"].get("rationale", ""), asset_root=asset_root),
                "elapsed_s": task.get("elapsed_s", 0),
            }
        )

    return {
        "source_name": source_name,
        "title": f"Bench Report: {config.get('engine_a', 'A')} vs {config.get('engine_b', 'B')}",
        "engine_a": config.get("engine_a", "engine_a"),
        "engine_b": config.get("engine_b", "engine_b"),
        "generator_label": generator_label(config),
        "judge_label": config.get("judge_model", "unknown"),
        "n": len(tasks),
        "dims": [DIMENSION_LABELS[dim] for dim in DIMENSIONS],
        "means_a": means_a,
        "means_b": means_b,
        "std_a": std_a,
        "std_b": std_b,
        "wins": wins,
        "per_task": per_task,
        "overall_a": round(summary.get("avg_total_a", 0.0), 2),
        "overall_b": round(summary.get("avg_total_b", 0.0), 2),
        "overall_wins_a": int(summary.get("wins_a", 0)),
        "overall_wins_b": int(summary.get("wins_b", 0)),
        "overall_ties": int(summary.get("ties", 0)),
        "avg_elapsed_s": round(summary.get("avg_elapsed_s", 0.0), 2),
        "group_size": config.get("group_size") or summary.get("pair_size", 1),
        "dataset_size": config.get("dataset_size", 0),
        "task_count": config.get("task_count", len(tasks)),
        "sample_count": config.get("sample_count"),
        "seed": config.get("seed"),
    }


def build_html(payload: dict, source_name: str, asset_root: Path | None = None) -> str:
    data = prepare_report_data(payload, source_name, asset_root=asset_root)
    data_json = json.dumps(data, ensure_ascii=False)
    title = html.escape(data["title"])
    engine_a = html.escape(data["engine_a"])
    engine_b = html.escape(data["engine_b"])
    generator = html.escape(data["generator_label"])
    judge = html.escape(data["judge_label"])
    source_file = html.escape(data["source_name"])
    group_size = html.escape(str(data["group_size"]))
    dataset_size = html.escape(str(data["dataset_size"]))
    task_count = html.escape(str(data["task_count"]))
    sample_count = html.escape(str(data["sample_count"])) if data["sample_count"] is not None else "all"
    seed = html.escape(str(data["seed"])) if data["seed"] is not None else "n/a"

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/d3@7"></script>
<script src="https://cdn.jsdelivr.net/npm/markmap-view@0.17"></script>
<script src="https://cdn.jsdelivr.net/npm/markmap-lib@0.17"></script>
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, "Helvetica Neue", Arial, sans-serif;
         max-width: 1180px; margin: 2em auto; padding: 0 1em; color: #222; }}
  h1 {{ border-bottom: 2px solid #333; padding-bottom: 0.3em; }}
  h2 {{ margin-top: 2em; border-bottom: 1px solid #ddd; padding-bottom: 0.2em; }}
  .meta {{ color: #666; font-size: 0.95em; }}
  .meta-grid {{ display: grid; grid-template-columns: repeat(5, minmax(0, 1fr)); gap: 0.8em; margin: 1em 0 1.5em; }}
  .meta-card, .stat-card {{ background: #f7f7f9; border: 1px solid #e0e0e6; border-radius: 8px; padding: 0.9em 1em; }}
  .stat-grid {{ display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 1em; margin: 1em 0; }}
  .stat-card .n {{ font-size: 2em; font-weight: 600; margin: 0.2em 0; }}
  .stat-card .a {{ color: #3b82f6; }}
  .stat-card .b {{ color: #ef4444; }}
  .chart-row {{ display: grid; grid-template-columns: 1fr 1fr; gap: 1.5em; }}
  .chart-wrap {{ background: white; border: 1px solid #eee; border-radius: 8px; padding: 1em; }}
  .chart-wrap canvas {{ max-height: 380px; }}
  .legend {{ font-size: 0.9em; color: #666; }}
  .ta {{ color: #3b82f6; font-weight: 600; }}
  .tb {{ color: #ef4444; font-weight: 600; }}
  footer {{ margin-top: 3em; font-size: 0.85em; color: #999; text-align: center; }}
  .mm-controls {{ display: flex; gap: 1em; align-items: center; margin: 1em 0; flex-wrap: wrap; }}
  .mm-controls select {{ flex: 1; min-width: 320px; padding: 0.4em; font-size: 1em; }}
  .mm-row {{ display: grid; grid-template-columns: 1fr 1fr; gap: 1em; }}
  .mm-panel {{ background: white; border: 1px solid #eee; border-radius: 8px; padding: 1em;
              overflow: auto; min-height: 520px; max-height: 85vh; }}
  .mm-panel h3 {{ margin: 0 0 0.6em 0; font-size: 1em; }}
  .mm-panel.a h3 {{ color: #3b82f6; }}
  .mm-panel.b h3 {{ color: #ef4444; }}
  .mm-panel .render {{ width: 100%; height: 640px; overflow: hidden; background: #fafafa;
                       border: 1px dashed #ddd; border-radius: 4px; }}
  .mm-panel .err {{ color: #b91c1c; font-size: 0.85em; white-space: pre-wrap; }}
  details.src {{ margin-top: 0.6em; font-size: 0.85em; color: #666; }}
  details.src pre {{ background: #f8f8fa; padding: 0.6em; border-radius: 4px; overflow: auto;
                    max-height: 220px; white-space: pre-wrap; word-break: break-word; }}
  .rationale {{ line-height: 1.55; }}
  .rationale h1, .rationale h2, .rationale h3, .rationale h4, .rationale h5, .rationale h6 {{ border: 0; margin: 0.7em 0 0.25em; padding: 0; }}
  .rationale p {{ margin: 0.45em 0; }}
  .rationale ul, .rationale ol {{ margin: 0.4em 0 0.7em 1.4em; }}
  .rationale pre {{ background: #f8f8fa; padding: 0.75em; border-radius: 6px; overflow: auto; }}
  .rationale .inline-code {{ background: #f1f3f5; padding: 0.1em 0.3em; border-radius: 4px; }}
  .spacer {{ height: 0.4em; }}
  @media (max-width: 900px) {{
    .meta-grid, .stat-grid, .chart-row, .mm-row {{ grid-template-columns: 1fr; }}
  }}
</style>
</head>
<body>

<h1>{title}</h1>
<p class="meta">Generator: {generator} · Judge: {judge} · Dimensions 1–5</p>

<div class="meta-grid">
  <div class="meta-card"><strong>Source</strong><div class="legend">{source_file}</div></div>
  <div class="meta-card"><strong>Group Size</strong><div class="legend">{group_size}</div></div>
  <div class="meta-card"><strong>Dataset Size</strong><div class="legend">{dataset_size}</div></div>
  <div class="meta-card"><strong>Tasks</strong><div class="legend">{task_count}</div></div>
  <div class="meta-card"><strong>Sample Count / Seed</strong><div class="legend">{sample_count} / {seed}</div></div>
</div>

<div class="stat-grid">
  <div class="stat-card">
    <div>Tasks judged</div>
    <div class="n" id="stat-n"></div>
  </div>
  <div class="stat-card">
    <div>Mean total (/25)</div>
    <div class="n"><span class="a" id="stat-a"></span> vs <span class="b" id="stat-b"></span></div>
  </div>
  <div class="stat-card">
    <div>Per-task wins</div>
    <div class="n"><span class="a" id="stat-wa"></span> · <span class="b" id="stat-wb"></span> · <span id="stat-t"></span></div>
    <div class="legend">{engine_a} · {engine_b} · Tie</div>
  </div>
  <div class="stat-card">
    <div>Avg elapsed</div>
    <div class="n" id="stat-elapsed"></div>
  </div>
</div>

<h2>1. Radar — overall profile</h2>
<div class="chart-row">
  <div class="chart-wrap"><canvas id="radar"></canvas></div>
  <div class="chart-wrap"><canvas id="bar-means"></canvas></div>
</div>

<h2>2. Per-dimension wins</h2>
<div class="chart-wrap"><canvas id="wins" style="max-height:320px"></canvas></div>

<h2>3. Per-task delta</h2>
<div class="chart-wrap"><canvas id="delta" style="max-height:520px"></canvas></div>

<h2>4. Side-by-side compare</h2>
<div class="mm-controls">
  <label for="mm-select"><strong>Pick a task:</strong></label>
  <select id="mm-select"></select>
</div>
<details class="src" id="task-meta">
  <summary><span id="meta-title">任务信息</span></summary>
  <div style="margin-top:0.6em">
    <div id="meta-files" class="legend"></div>
  </div>
</details>
<div class="mm-row">
  <div class="mm-panel a">
    <h3>{engine_a}（<span id="a-score"></span>）</h3>
    <div id="mm-a" class="render"></div>
    <details class="src"><summary>查看 Markdown 源码</summary><pre id="a-src"></pre></details>
    <details class="src"><summary>Judge rationale</summary><div id="a-rat" class="rationale"></div></details>
  </div>
  <div class="mm-panel b">
    <h3>{engine_b}（<span id="b-score"></span>）</h3>
    <div id="mm-b" class="render"></div>
    <details class="src"><summary>查看 Markdown 源码</summary><pre id="b-src"></pre></details>
    <details class="src"><summary>Judge rationale</summary><div id="b-rat" class="rationale"></div></details>
  </div>
</div>

<footer>Generated from <code>{source_file}</code> via <code>backend/scripts/render_bench_report.py</code></footer>

<script>
const DATA = {data_json};

document.getElementById('stat-n').textContent = DATA.n;
document.getElementById('stat-a').textContent = DATA.overall_a;
document.getElementById('stat-b').textContent = DATA.overall_b;
document.getElementById('stat-wa').textContent = DATA.overall_wins_a;
document.getElementById('stat-wb').textContent = DATA.overall_wins_b;
document.getElementById('stat-t').textContent = DATA.overall_ties;
document.getElementById('stat-elapsed').textContent = DATA.avg_elapsed_s + 's';

const BLUE = 'rgba(59,130,246,0.7)';
const BLUE_BORDER = 'rgb(59,130,246)';
const RED = 'rgba(239,68,68,0.7)';
const RED_BORDER = 'rgb(239,68,68)';

new Chart(document.getElementById('radar'), {{
  type: 'radar',
  data: {{
    labels: DATA.dims,
    datasets: [
      {{ label: DATA.engine_a, data: DATA.means_a, backgroundColor: BLUE, borderColor: BLUE_BORDER, pointBackgroundColor: BLUE_BORDER }},
      {{ label: DATA.engine_b, data: DATA.means_b, backgroundColor: RED, borderColor: RED_BORDER, pointBackgroundColor: RED_BORDER }}
    ]
  }},
  options: {{
    responsive: true,
    scales: {{ r: {{ min: 0, max: 5, ticks: {{ stepSize: 1 }} }} }},
    plugins: {{ title: {{ display: true, text: 'Mean score per dimension' }} }}
  }}
}});

new Chart(document.getElementById('bar-means'), {{
  type: 'bar',
  data: {{
    labels: DATA.dims,
    datasets: [
      {{ label: DATA.engine_a, data: DATA.means_a, backgroundColor: BLUE, borderColor: BLUE_BORDER, borderWidth: 1 }},
      {{ label: DATA.engine_b, data: DATA.means_b, backgroundColor: RED, borderColor: RED_BORDER, borderWidth: 1 }}
    ]
  }},
  options: {{
    responsive: true,
    scales: {{ y: {{ min: 0, max: 5, ticks: {{ stepSize: 1 }} }} }},
    plugins: {{
      title: {{ display: true, text: 'Mean (bars) — std in tooltip' }},
      tooltip: {{ callbacks: {{ afterLabel: (ctx) => {{
        const std = ctx.datasetIndex === 0 ? DATA.std_a : DATA.std_b;
        return '± ' + std[ctx.dataIndex];
      }} }} }}
    }}
  }}
}});

const winsA = DATA.wins.map(w => w[0]);
const winsB = DATA.wins.map(w => w[1]);
const ties = DATA.wins.map(w => w[2]);
new Chart(document.getElementById('wins'), {{
  type: 'bar',
  data: {{
    labels: DATA.dims,
    datasets: [
      {{ label: DATA.engine_a + ' wins', data: winsA, backgroundColor: BLUE }},
      {{ label: DATA.engine_b + ' wins', data: winsB, backgroundColor: RED }},
      {{ label: 'Ties', data: ties, backgroundColor: '#d1d5db' }}
    ]
  }},
  options: {{
    responsive: true,
    scales: {{ x: {{ stacked: true }}, y: {{ stacked: true, beginAtZero: true }} }},
    plugins: {{ title: {{ display: true, text: 'Per-dimension paired wins (n=' + DATA.n + ')' }} }}
  }}
}});

new Chart(document.getElementById('delta'), {{
  type: 'bar',
  data: {{
    labels: DATA.per_task.map(task => task.label),
    datasets: [
      {{
        label: DATA.engine_a + ' − ' + DATA.engine_b,
        data: DATA.per_task.map(task => task.delta),
        backgroundColor: DATA.per_task.map(task => task.delta >= 0 ? BLUE : RED),
        borderColor: DATA.per_task.map(task => task.delta >= 0 ? BLUE_BORDER : RED_BORDER),
        borderWidth: 1
      }}
    ]
  }},
  options: {{
    indexAxis: 'y',
    responsive: true,
    plugins: {{
      title: {{ display: true, text: 'Total score delta per task' }},
      tooltip: {{ callbacks: {{ label: (ctx) => {{
        const item = DATA.per_task[ctx.dataIndex];
        return DATA.engine_a + ' ' + item.a + ' vs ' + DATA.engine_b + ' ' + item.b + ' (Δ ' + item.delta + ')';
      }} }} }}
    }}
  }}
}});

const sel = document.getElementById('mm-select');
DATA.per_task.forEach((task, i) => {{
  const opt = document.createElement('option');
  opt.value = i;
  const sign = task.delta > 0 ? '+' : '';
  opt.textContent = `${{task.label}}  [{engine_a} ${{task.a}} vs {engine_b} ${{task.b}}, Δ${{sign}}${{task.delta}}]`;
  sel.appendChild(opt);
}});

const _mmInstances = {{}};
let _mmTransformer = null;
function getTransformer() {{
  if (_mmTransformer) return _mmTransformer;
  const T = window.markmap && window.markmap.Transformer;
  if (!T) return null;
  _mmTransformer = new T();
  return _mmTransformer;
}}

function renderPane(containerId, raw) {{
  const el = document.getElementById(containerId);
  if (_mmInstances[containerId]) {{
    try {{ _mmInstances[containerId].destroy(); }} catch (_) {{}}
    delete _mmInstances[containerId];
  }}
  el.innerHTML = '';
  if (!raw || !raw.trim()) {{
    el.innerHTML = '<p class="err" style="padding:1em">（缺少思维导图内容）</p>';
    return;
  }}
  try {{
    const Markmap = window.markmap && window.markmap.Markmap;
    const transformer = getTransformer();
    if (!Markmap || !transformer) {{
      el.innerHTML = '<p class="err" style="padding:1em">markmap 未加载</p>';
      return;
    }}
    const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    svg.setAttribute('style', 'width:100%;height:100%;display:block');
    el.appendChild(svg);
    const {{ root }} = transformer.transform(raw);
    const mm = Markmap.create(svg, {{ duration: 200, maxWidth: 320, spacingVertical: 5 }}, root);
    _mmInstances[containerId] = mm;
    setTimeout(() => {{ try {{ mm.fit(); }} catch (_) {{}} }}, 30);
  }} catch (e) {{
    el.innerHTML = '<p class="err" style="padding:1em"></p>';
    el.querySelector('.err').textContent = String(e);
  }}
}}

function scoreLine(score) {{
  return `coverage=${{score.coverage}}, hierarchy=${{score.hierarchy}}, balance=${{score.balance}}, conciseness=${{score.conciseness}}, accuracy=${{score.accuracy}}, total=${{
    score.coverage + score.hierarchy + score.balance + score.conciseness + score.accuracy
  }}`;
}}

function renderTask(index) {{
  const task = DATA.per_task[index];
  document.getElementById('meta-title').textContent = task.title;
  document.getElementById('meta-files').textContent = 'Files: ' + task.filenames.join(' | ') + ' · elapsed: ' + task.elapsed_s + 's';
  document.getElementById('a-score').textContent = scoreLine(task.score_a);
  document.getElementById('b-score').textContent = scoreLine(task.score_b);
  document.getElementById('a-src').textContent = task.mindmap_a || '';
  document.getElementById('b-src').textContent = task.mindmap_b || '';
  document.getElementById('a-rat').innerHTML = task.rationale_a_html || '<p>No rationale</p>';
  document.getElementById('b-rat').innerHTML = task.rationale_b_html || '<p>No rationale</p>';
  renderPane('mm-a', task.mindmap_a);
  renderPane('mm-b', task.mindmap_b);
}}

sel.addEventListener('change', (event) => renderTask(Number(event.target.value)));
if (DATA.per_task.length > 0) {{
  sel.value = '0';
  renderTask(0);
}}
</script>
</body>
</html>
"""


def main() -> int:
    parser = argparse.ArgumentParser(description="Render bench result JSON to HTML report")
    parser.add_argument("input", help="Path to bench result JSON")
    parser.add_argument("--output", help="Output HTML path")
    parser.add_argument("--asset-root", help="Optional asset root for relative images/links in rationale")
    args = parser.parse_args()

    input_path = Path(args.input).resolve()
    output_path = Path(args.output).resolve() if args.output else input_path.with_suffix(".html")
    asset_root = Path(args.asset_root).resolve() if args.asset_root else input_path.parent

    payload = json.loads(input_path.read_text(encoding="utf-8"))
    html_text = build_html(payload, input_path.name, asset_root=asset_root)
    output_path.write_text(html_text, encoding="utf-8")
    print(output_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
