"""
Application entry point. Wires together FastAPI, routes, DB init,
exception handlers and CORS. Run with:
    uvicorn app.main:app --reload
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

from app.api.routes import router
from app.core.config import settings
from app.core.exceptions import register_exception_handlers
from app.db.database import init_db
from app.core.logging_config import logger

app = FastAPI(
    title="Document Intelligence Platform",
    description="Extraction, validation and API platform for invoices and financial statements.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,  # set ALLOWED_ORIGINS in .env for production
    allow_methods=["*"],
    allow_headers=["*"],
)

register_exception_handlers(app)
app.include_router(router, prefix="/api")


@app.get("/", include_in_schema=False)
def root():
    # This is an API-only backend -- there is nothing meaningful to
    # show at the bare root. Rather than leave visitors (evaluators,
    # anyone poking at the deployed URL out of curiosity) staring at a
    # raw {"detail":"Not Found"} 404, send them straight to the
    # interactive API docs, which is the actual useful entry point.
    return RedirectResponse(url="/docs")


@app.on_event("startup")
def on_startup():
    init_db()
    logger.info("Database initialized. Application startup complete.")