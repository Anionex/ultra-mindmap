"""\
Bench 路由 — 对比不同引擎的思维导图生成质量。
使用 LLM-as-judge 进行盲评，输出 5 维度评分。
"""
import json
import random
import time
from concurrent.futures import ThreadPoolExecutor

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
    engine_a: str
    engine_b: str
    score_a: DimensionScore
    score_b: DimensionScore
    elapsed_s: float


def _build_judge_prompt(source_text: str, mindmap_a: str, mindmap_b: str) -> str:
    if len(source_text) > SOURCE_CHAR_CAP:
        source_text = source_text[:SOURCE_CHAR_CAP] + "\n\n[...truncated for length]"
    return f"""你是思维导图质量评审员。下面给你一篇文档的全文，以及两份由不同算法生成的思维导图 A 与 B。请客观对比后为每一份分别打分。

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


@router.post("/run", response_model=list[BenchResult])
def run_bench(req: BenchRequest, db: Session = Depends(get_db)):
    if not req.file_ids:
        raise AppError(code="INVALID_PARAMS", message="请至少选择一个文件")
    if req.engine_a == req.engine_b and req.params_a == req.params_b:
        raise AppError(code="INVALID_PARAMS", message="请选择不同的引擎或参数进行对比")

    engine_a = engine_base.get_engine(req.engine_a)
    engine_b = engine_base.get_engine(req.engine_b)

    documents = []
    for file_id in req.file_ids:
        record = db.query(UploadedFile).filter(UploadedFile.id == file_id).first()
        if not record:
            raise AppError(code="FILE_NOT_FOUND", message=f"文件不存在: {file_id}", status_code=404)
        content = parse_file(record.storage_path, record.file_type)
        documents.append({"id": file_id, "filename": record.filename, "content": content})

    results = []
    for doc_info in documents:
        doc = Document(title=doc_info["filename"], content=doc_info["content"])
        t0 = time.time()

        with ThreadPoolExecutor(max_workers=2) as executor:
            future_a = executor.submit(engine_a.generate, [doc], req.params_a)
            future_b = executor.submit(engine_b.generate, [doc], req.params_b)
            result_a = future_a.result()
            result_b = future_b.result()

        md_a = _json_tree_to_markdown(result_a)
        md_b = _json_tree_to_markdown(result_b)

        rng = random.Random(hash(doc_info["id"]) & 0xFFFFFFFF)
        if rng.random() < 0.5:
            label_a_is, label_b_is = req.engine_a, req.engine_b
            prompt_md_a, prompt_md_b = md_a, md_b
        else:
            label_a_is, label_b_is = req.engine_b, req.engine_a
            prompt_md_a, prompt_md_b = md_b, md_a

        prompt = _build_judge_prompt(doc_info["content"], prompt_md_a, prompt_md_b)
        raw_response = generate_mindmap_text(prompt, model=req.judge_model, temperature=0.1)
        parsed = _parse_judge_response(raw_response)

        dt = time.time() - t0

        if parsed and _validate_scores(parsed):
            if label_a_is == req.engine_a:
                score_a_raw = parsed["A"]
                score_b_raw = parsed["B"]
            else:
                score_a_raw = parsed["B"]
                score_b_raw = parsed["A"]
        else:
            score_a_raw = {d: 3 for d in DIMENSIONS}
            score_a_raw["rationale"] = "Judge failed to produce valid scores"
            score_b_raw = {d: 3 for d in DIMENSIONS}
            score_b_raw["rationale"] = "Judge failed to produce valid scores"

        results.append(BenchResult(
            file_id=doc_info["id"],
            filename=doc_info["filename"],
            engine_a=req.engine_a,
            engine_b=req.engine_b,
            score_a=DimensionScore(**score_a_raw),
            score_b=DimensionScore(**score_b_raw),
            elapsed_s=round(dt, 1),
        ))

    return results
