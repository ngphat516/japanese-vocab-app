import json
import logging
import time
from uuid import uuid4

from fastapi import Depends, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from starlette.exceptions import HTTPException

from app.common.schemas import DB
from app.core.config import get_settings
from app.core.exceptions import AppError
from app.core.rate_limit import check
from app.modules.auth.router import router as auth
from app.modules.dictionary.router import router as dictionary
from app.modules.imports.router import router as imports
from app.modules.notebook.router import router as notebook
from app.modules.search.router import router as search
from app.modules.textbooks.router import router as textbooks

app = FastAPI(title="Japanese Vocabulary Backend P0", version="0.1.0")
settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)
app.add_middleware(GZipMiddleware, minimum_size=1000)
logger = logging.getLogger("vocab.requests")
logging.basicConfig(level=logging.INFO, format="%(message)s")


def error_response(status, code, message, details=None):
    return JSONResponse(
        status_code=status,
        content={"error": {"code": code, "message": message, "details": details or {}}},
    )


@app.exception_handler(AppError)
async def handle_app_error(request, exc):
    return error_response(exc.status, exc.code, exc.message, exc.details)


@app.exception_handler(RequestValidationError)
async def handle_validation(request, exc):
    return error_response(
        422,
        "VALIDATION_ERROR",
        "Dữ liệu không hợp lệ",
        {
            "errors": [
                {"loc": list(e["loc"]), "type": e["type"], "message": e["msg"]}
                for e in exc.errors()
            ]
        },
    )


@app.exception_handler(HTTPException)
async def handle_http(request, exc):
    return error_response(exc.status_code, "HTTP_ERROR", str(exc.detail))


@app.exception_handler(Exception)
async def handle_unexpected(request, exc):
    logger.error(
        json.dumps(
            {
                "event": "unhandled_error",
                "request_id": getattr(request.state, "request_id", ""),
                "error_type": type(exc).__name__,
            }
        )
    )
    return error_response(500, "INTERNAL_ERROR", "Lỗi hệ thống")


@app.middleware("http")
async def request_log(request: Request, call_next):
    request.state.request_id = uuid4().hex
    start = time.monotonic()
    response = await call_next(request)
    response.headers["X-Request-ID"] = request.state.request_id
    logger.info(
        json.dumps(
            {
                "request_id": request.state.request_id,
                "method": request.method,
                "path": request.url.path,
                "status": response.status_code,
                "duration_ms": round((time.monotonic() - start) * 1000, 2),
            }
        )
    )
    return response


for router in [auth, textbooks, imports, search, notebook, dictionary]:
    app.include_router(router, prefix="/api/v1", dependencies=[Depends(check)])


@app.get("/health", tags=["health"])
@app.get("/api/v1/health", tags=["health"])
async def health(db: DB):
    try:
        await db.execute(text("SELECT 1"))
    except (SQLAlchemyError, OSError):
        return error_response(503, "DB_UNAVAILABLE", "Không kết nối được database")
    return {"status": "ok", "database": "ok"}
