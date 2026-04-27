import json
import os

from openai import OpenAI

from ..utils.errors import AppError

MINDMAP_MARKDOWN_SYSTEM_PROMPT = """\
你是一个思维导图生成器。根据用户提供的文本内容，输出一份用于 markmap 渲染的 Markdown 思维导图。

输出要求：
- 只输出 Markdown，不要输出 JSON
- 使用 ATX 标题语法（# / ## / ###）
- 整份内容必须是一棵思维导图，不要写解释、前言、总结、代码围栏、项目符号或段落
- 标题文本要简短，突出关键概念、论点和层级关系
- 思维导图层次清晰、要点完整、用词简练
"""

_client = None
_overrides: dict[str, str] = {}


def get_settings() -> dict[str, str]:
    return {
        "api_key": _overrides.get("api_key") or os.environ.get("OPENAI_API_KEY", ""),
        "api_base": _overrides.get("api_base") or os.environ.get("OPENAI_API_BASE", ""),
    }


def update_settings(settings: dict[str, str]) -> None:
    global _client
    changed = False
    for key in ("api_key", "api_base"):
        val = settings.get(key, "").strip()
        if val and val != _overrides.get(key):
            _overrides[key] = val
            changed = True
        elif not val and key in _overrides:
            del _overrides[key]
            changed = True
    if changed:
        _client = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        api_key = _overrides.get("api_key") or os.environ.get("OPENAI_API_KEY", "")
        if not api_key:
            raise AppError(
                code="LLM_API_ERROR",
                message="未配置 OpenAI API Key",
                detail="请设置环境变量 OPENAI_API_KEY 或在前端设置中填写",
            )
        base_url = _overrides.get("api_base") or os.environ.get("OPENAI_API_BASE") or None
        _client = OpenAI(api_key=api_key, base_url=base_url)
    return _client


def generate_mindmap_json(prompt: str, model: str = "gemini-3-flash-preview", temperature: float = 0.3) -> dict:
    try:
        client = _get_client()
        response = client.chat.completions.create(
            model=model,
            temperature=temperature,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
        )
        content = response.choices[0].message.content
        return json.loads(content)
    except AppError:
        raise
    except json.JSONDecodeError as e:
        raise AppError(code="LLM_API_ERROR", message="LLM 返回的内容不是有效的 JSON", detail=str(e))
    except Exception as e:
        raise AppError(code="LLM_API_ERROR", message="调用 LLM 失败", detail=str(e))


def generate_mindmap_markdown(prompt: str, model: str = "gemini-3-flash-preview", temperature: float = 0.3) -> str:
    try:
        client = _get_client()
        response = client.chat.completions.create(
            model=model,
            temperature=temperature,
            messages=[
                {"role": "system", "content": MINDMAP_MARKDOWN_SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
        )
        return response.choices[0].message.content or ""
    except AppError:
        raise
    except Exception as e:
        raise AppError(code="LLM_API_ERROR", message="调用 LLM 失败", detail=str(e))


def generate_mindmap_text(prompt: str, model: str = "gemini-3-flash-preview", temperature: float = 0.3) -> str:
    try:
        client = _get_client()
        response = client.chat.completions.create(
            model=model,
            temperature=temperature,
            messages=[
                {"role": "user", "content": prompt},
            ],
        )
        return response.choices[0].message.content or ""
    except AppError:
        raise
    except Exception as e:
        raise AppError(code="LLM_API_ERROR", message="调用 LLM 失败", detail=str(e))
