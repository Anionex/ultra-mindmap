from pydantic import BaseModel
from datetime import datetime


class FileResponse(BaseModel):
    id: str
    filename: str
    file_type: str
    file_size: int
    created_at: datetime

    class Config:
        from_attributes = True


class GenerateRequest(BaseModel):
    file_ids: list[str]
    engine: str
    params: dict = {}


class EngineInfo(BaseModel):
    name: str
    display_name: str
    description: str
    params_schema: dict
