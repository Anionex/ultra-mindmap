from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .database import Base, engine
from .utils.errors import AppError, app_error_handler
from .routers import files, mindmap

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Ultra MindMap")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_exception_handler(AppError, app_error_handler)
app.include_router(files.router, prefix="/api/files", tags=["files"])
app.include_router(mindmap.router, prefix="/api/mindmap", tags=["mindmap"])
