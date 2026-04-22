# Ultra MindMap — Design Spec

## Overview

A full-stack application (FastAPI + React) that generates mind maps from uploaded documents of unlimited length. Users upload documents to a file library, multi-select files, choose a generation engine with configurable parameters, and view the resulting mind map.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | FastAPI, SQLAlchemy + SQLite, OpenAI API, LangChain |
| Frontend | React (Vite), TailwindCSS 3.0+ (CDN), markmap, GSAP, lucide-react, Google Fonts |
| File parsing | python-docx, PyPDF2, built-in (txt/md) |

## Project Structure

```
ultra-mindmap/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI entry, CORS, error handler middleware
│   │   ├── database.py          # SQLite + SQLAlchemy setup
│   │   ├── models.py            # ORM models (UploadedFile, MindMap)
│   │   ├── schemas.py           # Pydantic request/response schemas
│   │   ├── routers/
│   │   │   ├── files.py         # File upload/list/delete endpoints
│   │   │   └── mindmap.py       # Mind map generation endpoint
│   │   ├── engines/
│   │   │   ├── base.py          # BaseEngine ABC + EngineRegistry
│   │   │   ├── direct.py        # DirectEngine — full text to LLM
│   │   │   └── chunked.py       # ChunkedEngine — split → per-chunk → merge
│   │   ├── services/
│   │   │   ├── file_service.py  # Parse txt/md/pdf/docx to plain text
│   │   │   └── llm_service.py   # OpenAI API wrapper
│   │   └── utils/
│   │       └── errors.py        # AppError class, exception handler
│   ├── uploads/                  # Local file storage
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── main.jsx
│   │   ├── App.jsx              # Root layout
│   │   ├── components/
│   │   │   ├── Layout.jsx       # Left panel + right main area
│   │   │   ├── FileLibrary.jsx  # Upload zone + file list + multi-select
│   │   │   ├── EnginePanel.jsx  # Engine selector + dynamic param form
│   │   │   ├── MindMapView.jsx  # markmap rendering
│   │   │   └── TipCard.jsx      # Info/warning/error notification card
│   │   ├── services/
│   │   │   └── api.js           # Axios-based API client
│   │   └── index.css            # Tailwind directives + custom styles
│   ├── index.html
│   ├── package.json
│   └── vite.config.js
```

## Engine Plugin System

### BaseEngine

```python
class BaseEngine(ABC):
    name: str           # unique identifier, e.g. "direct"
    display_name: str   # human-readable, e.g. "直接生成"
    description: str    # short description for UI

    @abstractmethod
    def get_params_schema(self) -> dict:
        """Return JSON Schema describing configurable parameters.
        Frontend renders a form from this schema automatically."""

    @abstractmethod
    async def generate(self, documents: list[Document], params: dict) -> dict:
        """Input: list of documents (each with title + content) and user params.
        Output: mind map tree as JSON dict."""
```

### EngineRegistry

A module-level registry that auto-discovers engine subclasses. The `/api/engines` endpoint returns all registered engines with their name, description, and params schema.

### DirectEngine

- Concatenates all documents with clear separators (document title as section header).
- Sends full text to OpenAI with a structured prompt requesting a JSON mind map tree.
- Each document becomes a top-level branch under the root.
- **Parameters**: model (gpt-4o / gpt-4o-mini), temperature (0.0–1.0), max_depth (2–6).

### ChunkedEngine

- For each document independently:
  1. Split using LangChain `RecursiveCharacterTextSplitter`.
  2. Generate a sub-mind-map for each chunk via OpenAI.
  3. Merge sub-mind-maps by combining branches under the document's title node.
- Each document is a top-level branch — natural separation preserved.
- **Parameters**: model, temperature, chunk_size (500–4000), chunk_overlap (0–500), max_depth (2–6).

## Mind Map Data Format

Unified JSON tree structure, directly compatible with markmap:

```json
{
  "name": "Root Topic",
  "children": [
    {
      "name": "Document 1 Title",
      "children": [
        {
          "name": "Topic A",
          "children": [
            {"name": "Sub-topic A1"},
            {"name": "Sub-topic A2"}
          ]
        },
        {
          "name": "Topic B",
          "children": []
        }
      ]
    },
    {
      "name": "Document 2 Title",
      "children": [...]
    }
  ]
}
```

## API Endpoints

### Files

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/files/upload` | Upload one or more files. Returns file metadata. |
| GET | `/api/files` | List all uploaded files with metadata. |
| DELETE | `/api/files/{id}` | Delete a file from storage and database. |

### Engines

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/engines` | List all engines with name, description, params schema. |

### Mind Map

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/mindmap/generate` | Generate mind map. Body: `{file_ids: [], engine: str, params: {}}`. Returns JSON mind map. |

## Database Schema

### UploadedFile

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| filename | String | Original filename |
| storage_path | String | Path on disk |
| file_type | String | Extension (txt/md/pdf/docx) |
| file_size | Integer | Size in bytes |
| created_at | DateTime | Upload timestamp |

## Frontend Design

### Visual Style

- **Theme**: Light, ChatGPT-inspired — white background, minimal borders, subtle gray tones, soft shadows.
- **Font**: Inter from Google Fonts.
- **Icons**: lucide-react exclusively, no emoji.
- **Animations**: GSAP for panel transitions, upload feedback, and mind map entrance.
- **TailwindCSS**: Via CDN in index.html.

### Layout

Two-column layout:

- **Left panel** (~350px, fixed): File library at top, engine config below, generate button at bottom.
- **Right main area** (flex-grow): Mind map rendered via markmap, full-size, supports zoom/pan.

### File Library Component

- Drag-and-drop upload zone with file type validation.
- File list with checkboxes for multi-select.
- File metadata display (name, size, date).
- Delete button per file.

### Engine Panel Component

- Dropdown to select engine.
- Dynamic form rendered from engine's JSON Schema (sliders for numeric ranges, dropdowns for enums).
- Defaults pre-filled from schema.

### TipCard Component

- Left border + tinted background.
- Variants: info (blue), success (green), warning (yellow), error (red).
- Auto-dismiss after timeout or manual close.

## Error Handling

### Backend

- Custom `AppError` exception class with `code`, `message`, `detail` fields.
- FastAPI exception handler middleware catches `AppError` and returns structured JSON:
  ```json
  {"error": {"code": "FILE_PARSE_ERROR", "message": "无法解析 PDF 文件", "detail": "..."}}
  ```
- Error codes: `FILE_PARSE_ERROR`, `FILE_NOT_FOUND`, `LLM_API_ERROR`, `INVALID_ENGINE`, `INVALID_PARAMS`, `FILE_TOO_LARGE`.

### Frontend

- API client intercepts errors and shows TipCard with appropriate variant.
- Network errors show a generic connection error message.
- Generation errors show specific error messages from the backend.

## Supported File Formats

| Format | Library | Notes |
|--------|---------|-------|
| .txt | built-in | UTF-8 read |
| .md | built-in | UTF-8 read (treated as plain text for LLM) |
| .pdf | PyPDF2 | Extract text from all pages |
| .docx | python-docx | Extract paragraph text |

## Non-Goals (Explicitly Out of Scope)

- Authentication / multi-user
- Mind map editing in the UI
- Export to image/PDF
- Real-time collaboration
- File versioning
