"""\
Bench 路由 — 对比不同引擎的思维导图生成质量。
使用 LLM-as-judge 进行盲评，输出 5 维度评分。
"""
import json
import itertools
import logging
import random
import time
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import UploadedFile
from ..engines import base as engine_base
from ..engines.base import Document
from ..services.file_service import parse_file
from ..services.llm_service import generate_mindmap_text
from ..utils.errors import AppError

router = APIRouter()

DIMENSIONS = ["coverage", "hierarchy", "balance", "conciseness", "accuracy"]

SOURCE_CHAR_CAP = 180000


class BenchRequest(BaseModel):
    file_ids: list[str]
    engine_a: str
    params_a: dict = {}
    engine_b: str
    params_b: dict = {}
    judge_model: str = "gpt-4o"


class BenchBatchRequest(BenchRequest):
    pair_size: int = 2
    sample_count: int | None = None
    sampling_mode: str = "all_pairs"
    seed: int = 0


class DimensionScore(BaseModel):
    coverage: int
    hierarchy: int
    balance: int
    conciseness: int
    accuracy: int
    rationale: str = ""


class BenchResult(BaseModel):
    file_id: str
    filename: str
    file_ids: list[str] = []
    filenames: list[str] = []
    engine_a: str
    engine_b: str
    score_a: DimensionScore
    score_b: DimensionScore
    mindmap_a: str = ""
    mindmap_b: str = ""
    elapsed_s: float


class BenchBatchSummary(BaseModel):
    task_count: int
    pair_size: int
    wins_a: int
    wins_b: int
    ties: int
    avg_total_a: float
    avg_total_b: float
    avg_elapsed_s: float


class BenchBatchResponse(BaseModel):
    tasks: list[BenchResult]
    summary: BenchBatchSummary


def _build_judge_prompt(source_text: str, mindmap_a: str, mindmap_b: str) -> str:
    if len(source_text) > SOURCE_CHAR_CAP:
        source_text = source_text[:SOURCE_CHAR_CAP] + "\n\n[...truncated for length]"
    return f"""你是思维导图质量评审员。下面给你一组文档的全文，以及两份由不同算法生成的思维导图 A 与 B。请客观对比后为每一份分别打分。

评分维度（各 1-5 分，5 最佳）：
- coverage (全文覆盖): 是否完整覆盖文档的主要章节与主题
- hierarchy (层级合理性): 父子关系是否合理、深度利用是否充分
- balance (分支均衡性): 各主分支规模是否均衡
- conciseness (简洁性): 节点用短语而非长句
- accuracy (忠实度): 关键术语、数字、论点是否准确保留

输出严格 JSON（不得含 Markdown 代码围栏或任何解释文字）。输出格式：
{{
  "A": {{"coverage": int, "hierarchy": int, "balance": int, "conciseness": int, "accuracy": int, "rationale": "..."}},
  "B": {{"coverage": int, "hierarchy": int, "balance": int, "conciseness": int, "accuracy": int, "rationale": "..."}}
}}

[SOURCE]
{source_text}

[MINDMAP A]
{mindmap_a}

[MINDMAP B]
{mindmap_b}

请直接输出 JSON："""


def _json_tree_to_markdown(node: dict, depth: int = 1) -> str:
    lines = []
    name = node.get("name", "")
    if name:
        lines.append(f"{'#' * depth} {name}")
    for child in node.get("children", []):
        lines.extend(_json_tree_to_markdown(child, depth + 1).split("\n"))
    return "\n".join(lines)


def _parse_judge_response(raw: str) -> dict | None:
    if not raw:
        return None
    text = raw.strip()
    if text.startswith("```"):
        lines = [l for l in text.split("\n") if not l.strip().startswith("```")]
        text = "\n".join(lines)
    try:
        return json.loads(text)
    except Exception:
        pass
    import re
    m = re.search(r"\{[\s\S]*\}", text)
    if m:
        try:
            return json.loads(m.group())
        except Exception:
            pass
    return None


def _validate_scores(obj) -> bool:
    if not isinstance(obj, dict):
        return False
    for label in ("A", "B"):
        if label not in obj or not isinstance(obj[label], dict):
            return False
        for dim in DIMENSIONS:
            v = obj[label].get(dim)
            if not isinstance(v, (int, float)) or not (1 <= v <= 5):
                return False
    return True


def _load_documents(file_ids: list[str], db: Session) -> list[dict]:
    documents = []
    for file_id in file_ids:
        record = db.query(UploadedFile).filter(UploadedFile.id == file_id).first()
        if not record:
            raise AppError(code="FILE_NOT_FOUND", message=f"文件不存在: {file_id}", status_code=404)
        content = parse_file(record.storage_path, record.file_type)
        documents.append({"id": file_id, "filename": record.filename, "content": content})
    return documents


def _format_source_documents(documents: list[dict]) -> str:
    return "\n\n".join(
        f"=== 文档: {doc['filename']} ===\n{doc['content']}"
        for doc in documents
    )


def _evaluate_document_group(
    documents: list[dict],
    engine_a,
    engine_b,
    req_engine_a: str,
    req_engine_b: str,
    params_a: dict,
    params_b: dict,
    judge_model: str,
) -> BenchResult:
    file_ids = [doc["id"] for doc in documents]
    filenames = [doc["filename"] for doc in documents]
    label = filenames[0] if len(filenames) == 1 else f"{filenames[0]} +{len(filenames) - 1}"
    file_id = file_ids[0] if len(file_ids) == 1 else ",".join(file_ids)
    source_text = _format_source_documents(documents)
    task_documents = [Document(title=doc["filename"], content=doc["content"]) for doc in documents]

    logger.info("Processing bench task: files=%s", filenames)
    t0 = time.time()

    with ThreadPoolExecutor(max_workers=2) as executor:
        future_a = executor.submit(engine_a.generate, task_documents, params_a)
        future_b = executor.submit(engine_b.generate, task_documents, params_b)
        result_a = future_a.result()
        result_b = future_b.result()

    md_a = _json_tree_to_markdown(result_a)
    md_b = _json_tree_to_markdown(result_b)

    rng = random.Random(hash(tuple(file_ids)) & 0xFFFFFFFF)
    if rng.random() < 0.5:
        label_a_is, label_b_is = req_engine_a, req_engine_b
        prompt_md_a, prompt_md_b = md_a, md_b
    else:
        label_a_is, label_b_is = req_engine_b, req_engine_a
        prompt_md_a, prompt_md_b = md_b, md_a

    prompt = _build_judge_prompt(source_text, prompt_md_a, prompt_md_b)
    raw_response = generate_mindmap_text(prompt, model=judge_model, temperature=0.1)
    parsed = _parse_judge_response(raw_response)
    logger.info("Judge response parsed=%s for task=%s", parsed is not None, filenames)

    dt = time.time() - t0

    if parsed and _validate_scores(parsed):
        if label_a_is == req_engine_a:
            score_a_raw = parsed["A"]
            score_b_raw = parsed["B"]
        else:
            score_a_raw = parsed["B"]
            score_b_raw = parsed["A"]
    else:
        logger.warning("Judge failed for task=%s, using default scores. raw=%s", filenames, raw_response[:200] if raw_response else None)
        score_a_raw = {d: 3 for d in DIMENSIONS}
        score_a_raw["rationale"] = "Judge failed to produce valid scores"
        score_b_raw = {d: 3 for d in DIMENSIONS}
        score_b_raw["rationale"] = "Judge failed to produce valid scores"

    return BenchResult(
        file_id=file_id,
        filename=label,
        file_ids=file_ids,
        filenames=filenames,
        engine_a=req_engine_a,
        engine_b=req_engine_b,
        score_a=DimensionScore(**score_a_raw),
        score_b=DimensionScore(**score_b_raw),
        mindmap_a=md_a,
        mindmap_b=md_b,
        elapsed_s=round(dt, 1),
    )


def _choose_document_groups(documents: list[dict], pair_size: int, sampling_mode: str, sample_count: int | None, seed: int) -> list[list[dict]]:
    if pair_size < 2:
        raise AppError(code="INVALID_PARAMS", message="pair_size 至少为 2")
    if len(documents) < pair_size:
        raise AppError(code="INVALID_PARAMS", message=f"至少选择 {pair_size} 个文件")

    groups = [list(group) for group in itertools.combinations(documents, pair_size)]
    if sampling_mode == "all_pairs":
        return groups
    if sampling_mode != "random":
        raise AppError(code="INVALID_PARAMS", message="sampling_mode 仅支持 all_pairs 或 random")

    if sample_count is None or sample_count <= 0:
        raise AppError(code="INVALID_PARAMS", message="random 模式下 sample_count 必须大于 0")

    rng = random.Random(seed)
    if sample_count >= len(groups):
        rng.shuffle(groups)
        return groups
    return rng.sample(groups, sample_count)


def _build_batch_summary(results: list[BenchResult], pair_size: int) -> BenchBatchSummary:
    totals_a = []
    totals_b = []
    wins_a = 0
    wins_b = 0
    ties = 0

    for result in results:
        total_a = sum(getattr(result.score_a, dim) for dim in DIMENSIONS)
        total_b = sum(getattr(result.score_b, dim) for dim in DIMENSIONS)
        totals_a.append(total_a)
        totals_b.append(total_b)
        if total_a > total_b:
            wins_a += 1
        elif total_b > total_a:
            wins_b += 1
        else:
            ties += 1

    avg_elapsed = sum(result.elapsed_s for result in results) / len(results) if results else 0.0

    return BenchBatchSummary(
        task_count=len(results),
        pair_size=pair_size,
        wins_a=wins_a,
        wins_b=wins_b,
        ties=ties,
        avg_total_a=round(sum(totals_a) / len(totals_a), 2) if totals_a else 0.0,
        avg_total_b=round(sum(totals_b) / len(totals_b), 2) if totals_b else 0.0,
        avg_elapsed_s=round(avg_elapsed, 2),
    )


@router.post("/run", response_model=list[BenchResult])
def run_bench(req: BenchRequest, db: Session = Depends(get_db)):
    if not req.file_ids:
        raise AppError(code="INVALID_PARAMS", message="请至少选择一个文件")
    if req.engine_a == req.engine_b and req.params_a == req.params_b:
        raise AppError(code="INVALID_PARAMS", message="请选择不同的引擎或参数进行对比")

    engine_a = engine_base.get_engine(req.engine_a)
    engine_b = engine_base.get_engine(req.engine_b)
    documents = _load_documents(req.file_ids, db)

    logger.info("Bench start: engine_a=%s, engine_b=%s, files=%d", req.engine_a, req.engine_b, len(documents))
    result = _evaluate_document_group(
        documents=documents,
        engine_a=engine_a,
        engine_b=engine_b,
        req_engine_a=req.engine_a,
        req_engine_b=req.engine_b,
        params_a=req.params_a,
        params_b=req.params_b,
        judge_model=req.judge_model,
    )
    return [result]


@router.post("/run-batch", response_model=BenchBatchResponse)
def run_bench_batch(req: BenchBatchRequest, db: Session = Depends(get_db)):
    if not req.file_ids:
        raise AppError(code="INVALID_PARAMS", message="请至少选择一个文件")
    if req.engine_a == req.engine_b and req.params_a == req.params_b:
        raise AppError(code="INVALID_PARAMS", message="请选择不同的引擎或参数进行对比")

    engine_a = engine_base.get_engine(req.engine_a)
    engine_b = engine_base.get_engine(req.engine_b)
    documents = _load_documents(req.file_ids, db)
    groups = _choose_document_groups(
        documents=documents,
        pair_size=req.pair_size,
        sampling_mode=req.sampling_mode,
        sample_count=req.sample_count,
        seed=req.seed,
    )

    logger.info(
        "Bench batch start: engine_a=%s, engine_b=%s, files=%d, tasks=%d, pair_size=%d, sampling_mode=%s",
        req.engine_a,
        req.engine_b,
        len(documents),
        len(groups),
        req.pair_size,
        req.sampling_mode,
    )

    results = [
        _evaluate_document_group(
            documents=group,
            engine_a=engine_a,
            engine_b=engine_b,
            req_engine_a=req.engine_a,
            req_engine_b=req.engine_b,
            params_a=req.params_a,
            params_b=req.params_b,
            judge_model=req.judge_model,
        )
        for group in groups
    ]

    return BenchBatchResponse(
        tasks=results,
        summary=_build_batch_summary(results, pair_size=req.pair_size),
    )
