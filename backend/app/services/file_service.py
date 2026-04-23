from pathlib import Path

from PyPDF2 import PdfReader
from docx import Document

from ..utils.errors import AppError

SUPPORTED_TYPES = {".txt", ".md", ".pdf", ".docx"}


def validate_file_type(filename: str) -> str:
    ext = Path(filename).suffix.lower()
    if ext not in SUPPORTED_TYPES:
        raise AppError(
            code="INVALID_FILE_TYPE",
            message=f"不支持的文件类型: {ext}",
            detail=f"支持的格式: {', '.join(SUPPORTED_TYPES)}",
        )
    return ext


def parse_file(file_path: str, file_type: str) -> str:
    parsers = {
        ".txt": _parse_text,
        ".md": _parse_text,
        ".pdf": _parse_pdf,
        ".docx": _parse_docx,
    }
    parser = parsers.get(file_type)
    if not parser:
        raise AppError(code="FILE_PARSE_ERROR", message=f"无法解析文件类型: {file_type}")
    try:
        return parser(file_path)
    except AppError:
        raise
    except Exception as e:
        raise AppError(
            code="FILE_PARSE_ERROR",
            message=f"文件解析失败",
            detail=str(e),
        )


def _parse_text(file_path: str) -> str:
    return Path(file_path).read_text(encoding="utf-8")


def _parse_pdf(file_path: str) -> str:
    reader = PdfReader(file_path)
    pages = [page.extract_text() or "" for page in reader.pages]
    text = "\n\n".join(pages).strip()
    if not text:
        raise AppError(code="FILE_PARSE_ERROR", message="PDF 文件中未提取到文本内容")
    return text


def _parse_docx(file_path: str) -> str:
    doc = Document(file_path)
    text = "\n\n".join(p.text for p in doc.paragraphs if p.text.strip())
    if not text:
        raise AppError(code="FILE_PARSE_ERROR", message="DOCX 文件中未提取到文本内容")
    return text
