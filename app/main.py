# app/main.py
# Job of this file: create the app, create tables at startup, add the safety
# middleware (logging, rate limit, headers, CORS, size limit), plug in routers,
# and turn every error into the same clean JSON shape.

import logging
import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

import app.models  # noqa: F401  (registers all 8 models, so create_all sees them)
from app.core.config import settings
from app.core.database import Base, engine
from app.core.exceptions import AppError
from app.core.limiter import limiter
from app.core.logging_config import setup_logging
from app.routers import auth, circles, complaints, plans, recharges, subscribers, usage

setup_logging()
request_log = logging.getLogger("app.request")
error_log = logging.getLogger("app.error")

MAX_BODY_BYTES = 1_000_000  # 1 MB: bigger requests are refused


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Runs once at startup (before 'yield') and once at shutdown (after)."""
    Base.metadata.create_all(bind=engine)  # creates missing tables, keeps data
    yield


app = FastAPI(
    title="Telecom REST API Backend",
    description="Prepaid plan comparison and recharge backend for a fictional Ahmedabad MVNO.",
    version="1.0.0",
    lifespan=lifespan,
)

# ---------- rate limiting ----------
app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)


@app.exception_handler(RateLimitExceeded)
async def handle_rate_limit(request: Request, exc: RateLimitExceeded):
    return JSONResponse(
        status_code=429,
        content={"error": {"code": 429, "message": "Too many requests. Please try again later."}},
    )


# ---------- request pipeline: size limit, request id, security headers, logging ----------
@app.middleware("http")
async def request_pipeline(request: Request, call_next):
    request_id = uuid.uuid4().hex[:12]
    request.state.request_id = request_id
    started = time.perf_counter()

    # Refuse huge bodies early (unrestricted resource consumption, an OWASP API risk).
    length = request.headers.get("content-length")
    if length and length.isdigit() and int(length) > MAX_BODY_BYTES:
        return JSONResponse(
            status_code=413,
            content={"error": {"code": 413, "message": "Request body too large"}},
        )

    response = await call_next(request)

    response.headers["X-Request-ID"] = request_id
    response.headers["X-Content-Type-Options"] = "nosniff"  # browser must not guess types
    response.headers["X-Frame-Options"] = "DENY"  # nobody may put us in an iframe
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Cache-Control"] = "no-store"  # API replies are never cached

    # One JSON line per request. We log the path only (no query string, no headers,
    # no body), so passwords and tokens never reach the logs.
    request_log.info(
        "request",
        extra={"fields": {
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "status": response.status_code,
            "duration_ms": round((time.perf_counter() - started) * 1000, 1),
        }},
    )
    return response


# ---------- CORS: only listed browser origins may call the API ----------
origins = [o.strip() for o in settings.CORS_ORIGINS.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=False,  # we use a Bearer header, not cookies
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)


# ---------- central error handling: every error has the same JSON shape ----------
@app.exception_handler(AppError)
async def handle_app_error(request: Request, exc: AppError):
    """Our own errors (404, 409, 403, 401, 422) raised by services/dependencies."""
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": exc.status_code, "message": exc.message}},
    )


@app.exception_handler(RequestValidationError)
async def handle_validation_error(request: Request, exc: RequestValidationError):
    """Bad input (wrong type, price below 0, page_size 500...)."""
    details = [
        {
            "field": ".".join(str(part) for part in error["loc"] if part != "body"),
            "message": error["msg"],
        }
        for error in exc.errors()
    ]
    return JSONResponse(
        status_code=422,
        content={"error": {"code": 422, "message": "Validation failed", "details": details}},
    )


@app.exception_handler(Exception)
async def handle_unexpected_error(request: Request, exc: Exception):
    """A bug. The stack trace goes to the SERVER log only; the client sees a
    generic message plus the request id, so you can find the log line."""
    request_id = getattr(request.state, "request_id", None)
    error_log.error(
        "unhandled error",
        exc_info=exc,
        extra={"fields": {"request_id": request_id, "path": request.url.path}},
    )
    return JSONResponse(
        status_code=500,
        content={"error": {"code": 500, "message": "Internal server error"}},
    )


# ---------- routers ----------
for router_module in (auth, circles, plans, subscribers, recharges, usage, complaints):
    app.include_router(router_module.router)


@app.get("/health", tags=["Health"])
def health_check():
    """A tiny endpoint to check that the app is running."""
    return {"status": "ok"}