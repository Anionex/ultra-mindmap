import os
import uuid
import shutil
from pathlib import Path

from fastapi import APIRouter, UploadFile, File, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import UploadedFile
from ..schemas import FileResponse
from ..services.file_service import validate_file_type
from ..utils.errors import AppError

router = APIRouter()

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)


@router.post("/upload", response_model=list[FileResponse])
def upload_files(files: list[UploadFile] = File(...), db: Session = Depends(get_db)):
    results = []
    for f in files:
        file_type = validate_file_type(f.filename)
        file_id = str(uuid.uuid4())
        storage_name = f"{file_id}{file_type}"
        storage_path = os.path.join(UPLOAD_DIR, storage_name)

        with open(storage_path, "wb") as buf:
            shutil.copyfileobj(f.file, buf)

        file_size = os.path.getsize(storage_path)
        record = UploadedFile(
            id=file_id,
            filename=f.filename,
            storage_path=storage_path,
            file_type=file_type,
            file_size=file_size,
        )
        db.add(record)
        db.commit()
        db.refresh(record)
        results.append(record)
    return results


@router.get("", response_model=list[FileResponse])
def list_files(db: Session = Depends(get_db)):
    return db.query(UploadedFile).order_by(UploadedFile.created_at.desc()).all()


@router.delete("/{file_id}")
def delete_file(file_id: str, db: Session = Depends(get_db)):
    record = db.query(UploadedFile).filter(UploadedFile.id == file_id).first()
    if not record:
        raise AppError(code="FILE_NOT_FOUND", message="文件不存在", status_code=404)
    if os.path.exists(record.storage_path):
        os.remove(record.storage_path)
    db.delete(record)
    db.commit()
    return {"ok": True}
