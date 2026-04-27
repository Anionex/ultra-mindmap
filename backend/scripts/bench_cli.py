import argparse
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import sys

from sqlalchemy import select
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
load_dotenv(Path(__file__).resolve().parents[2] / ".env")

from app.database import SessionLocal
from app.engines import base as engine_base
import app.engines  # noqa: F401
from app.models import UploadedFile
from app.routers.bench import _build_batch_summary, _choose_document_groups, _evaluate_document_group
from app.services.file_service import parse_file


def _parse_json_arg(raw: str | None) -> dict:
    if not raw:
        return {}
    value = json.loads(raw)
    if not isinstance(value, dict):
        raise ValueError("JSON params must be an object")
    return value


def _load_dataset(all_files: bool, file_ids: list[str], filenames: list[str]) -> list[dict]:
    with SessionLocal() as db:
        query = select(UploadedFile).order_by(UploadedFile.created_at.desc())
        records = list(db.scalars(query))

    if file_ids:
        id_set = set(file_ids)
        records = [record for record in records if record.id in id_set]
    elif filenames:
        name_set = set(filenames)
        records = [record for record in records if record.filename in name_set]
    elif not all_files:
        raise ValueError("Choose files with --file-id, --filename, or --all-files")

    documents = [
        {
            "id": record.id,
            "filename": record.filename,
            "content": parse_file(record.storage_path, record.file_type),
        }
        for record in records
    ]
    if not documents:
        raise ValueError("No matching files found in bench dataset")
    return documents


def _build_tasks(documents: list[dict], group_size: int, sample_count: int | None, seed: int) -> list[list[dict]]:
    if group_size == 1:
        return [[doc] for doc in documents]
    if len(documents) == 1:
        return [documents]
    return _choose_document_groups(
        documents=documents,
        pair_size=group_size,
        sampling_mode="random" if sample_count else "all_pairs",
        sample_count=sample_count,
        seed=seed,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Batch bench for mindmap engines")
    parser.add_argument("--engine-a", required=True)
    parser.add_argument("--engine-b", required=True)
    parser.add_argument("--judge-model", default="gpt-4o")
    parser.add_argument("--params-a", default="{}")
    parser.add_argument("--params-b", default="{}")
    parser.add_argument("--group-size", "-k", type=int, default=2)
    parser.add_argument("--sample-count", type=int, default=None)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--file-id", action="append", default=[])
    parser.add_argument("--filename", action="append", default=[])
    parser.add_argument("--all-files", action="store_true")
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--output", default=None)
    args = parser.parse_args()

    params_a = _parse_json_arg(args.params_a)
    params_b = _parse_json_arg(args.params_b)
    if args.engine_a == args.engine_b and params_a == params_b:
        raise ValueError("Choose different engines or different params for bench")

    documents = _load_dataset(
        all_files=args.all_files,
        file_ids=args.file_id,
        filenames=args.filename,
    )
    tasks = _build_tasks(
        documents=documents,
        group_size=args.group_size,
        sample_count=args.sample_count,
        seed=args.seed,
    )

    engine_a = engine_base.get_engine(args.engine_a)
    engine_b = engine_base.get_engine(args.engine_b)

    if args.workers < 1:
        raise ValueError("--workers must be at least 1")

    def run_task(task: list[dict]):
        return _evaluate_document_group(
            documents=task,
            engine_a=engine_a,
            engine_b=engine_b,
            req_engine_a=args.engine_a,
            req_engine_b=args.engine_b,
            params_a=params_a,
            params_b=params_b,
            judge_model=args.judge_model,
        )

    if args.workers == 1:
        results = [run_task(task) for task in tasks]
    else:
        with ThreadPoolExecutor(max_workers=args.workers) as executor:
            results = list(executor.map(run_task, tasks))
    summary = _build_batch_summary(results, pair_size=args.group_size)
    payload = {
        "config": {
            "engine_a": args.engine_a,
            "engine_b": args.engine_b,
            "judge_model": args.judge_model,
            "group_size": args.group_size,
            "sample_count": args.sample_count,
            "seed": args.seed,
            "workers": args.workers,
            "dataset_size": len(documents),
            "task_count": len(results),
        },
        "summary": summary.model_dump(),
        "tasks": [result.model_dump() for result in results],
    }

    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2))

    print(
        json.dumps(
            {
                "dataset_size": len(documents),
                "task_count": summary.task_count,
                "group_size": args.group_size,
                "wins_a": summary.wins_a,
                "wins_b": summary.wins_b,
                "ties": summary.ties,
                "avg_total_a": summary.avg_total_a,
                "avg_total_b": summary.avg_total_b,
                "avg_elapsed_s": summary.avg_elapsed_s,
                "output": args.output,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
