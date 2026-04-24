from fastapi import APIRouter
from pydantic import BaseModel

from ..services.llm_service import get_settings, update_settings

router = APIRouter()


class SettingsPayload(BaseModel):
    api_key: str = ""
    api_base: str = ""


@router.get("")
def read_settings():
    s = get_settings()
    key = s["api_key"]
    return {
        "api_key_set": bool(key),
        "api_key_hint": key[:4] + "***" + key[-4:] if len(key) > 8 else ("***" if key else ""),
        "api_base": s["api_base"],
    }


@router.put("")
def write_settings(payload: SettingsPayload):
    update_settings(payload.model_dump())
    return read_settings()
