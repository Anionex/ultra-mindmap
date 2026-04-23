from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import UploadedFile
from ..schemas import GenerateRequest, EngineInfo
from ..engines import base as engine_base  # engines/__init__.py triggers registration
from ..engines.base import Document
from ..services.file_service import parse_file
from ..utils.errors import AppError

router = APIRouter()


@router.get("/engines", response_model=list[EngineInfo])
def list_engines():
    return [
        EngineInfo(
            name=e.name,
            display_name=e.display_name,
            description=e.description,
            params_schema=e.get_params_schema(),
        )
        for e in engine_base.list_engines()
    ]


@router.post("/generate")
def generate_mindmap(req: GenerateRequest, db: Session = Depends(get_db)):
    if not req.file_ids:
        raise AppError(code="INVALID_PARAMS", message="请至少选择一个文件")

    engine = engine_base.get_engine(req.engine)

    documents = []
    for file_id in req.file_ids:
        record = db.query(UploadedFile).filter(UploadedFile.id == file_id).first()
        if not record:
            raise AppError(code="FILE_NOT_FOUND", message=f"文件不存在: {file_id}", status_code=404)
        content = parse_file(record.storage_path, record.file_type)
        documents.append(Document(title=record.filename, content=content))

    result = engine.generate(documents, req.params)
    return result
