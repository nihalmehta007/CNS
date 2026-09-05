"""
backend/main.py — FastAPI application for Crimson Nyx Studios.

Serves the static frontend, a contact-form API with email notifications,
CSRF-protected forms, and a password-protected admin dashboard.
"""

from __future__ import annotations

import html
import logging
import re
import secrets
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Query, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.staticfiles import StaticFiles
from itsdangerous import BadSignature, URLSafeTimedSerializer
from passlib.hash import bcrypt
from pydantic import BaseModel, Field

from backend.config import settings
from backend.db import close_db, db_health, init_db, insert_message, list_messages
from backend.mail import send_contact_email

log = logging.getLogger(__name__)

# ── Paths ────────────────────────────────────────────────────────────────────
FRONTEND_DIR = Path(__file__).resolve().parents[1] / "frontend"
ADMIN_PAGE = Path(__file__).resolve().parent / "admin.html"

# ── Constants ────────────────────────────────────────────────────────────────
EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
DEV_ORIGIN_RE = re.compile(r"^https?://(localhost|127\.0\.0\.1|\[::1\])(:\d+)?$", re.IGNORECASE)
ALLOWED_SERVICES = {
    "Graphic Design",
    "Website Development",
    "Game Development",
    "App Development",
}

# CSRF token max age: 2 hours
CSRF_MAX_AGE = 7200

# ── Rate limiter state ───────────────────────────────────────────────────────
_RATE: dict[str, list[float]] = {}
_LAST_CLEANUP = time.time()

security = HTTPBasic()
csrf_serializer = URLSafeTimedSerializer(settings.SECRET_KEY, salt="csrf-token")


# ── Request models ───────────────────────────────────────────────────────────

class ContactPayload(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    email: str = Field(min_length=5, max_length=200)
    service: str = Field(min_length=2, max_length=80)
    message: str = Field(min_length=10, max_length=3000)
    company: str | None = Field(default=None, max_length=0)  # honeypot (must be empty)


# ── Helpers ──────────────────────────────────────────────────────────────────

def _get_client_ip(request: Request) -> str:
    """Extract client IP, preferring the X-Forwarded-For header if behind a proxy."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    host = request.client.host if request.client else "unknown"
    return host


def _rate_limit(ip: str) -> None:
    """Enforce per-IP rate limiting.  Raises 429 with Retry-After header."""
    global _LAST_CLEANUP
    now = time.time()
    window = settings.RATE_LIMIT_WINDOW
    limit = settings.RATE_LIMIT_MAX

    # Periodic cleanup every 60 s to prevent memory leaks from IP churn
    if now - _LAST_CLEANUP > 60:
        expired = [k for k, v in _RATE.items() if not [t for t in v if now - t < window]]
        for k in expired:
            del _RATE[k]
        _LAST_CLEANUP = now

    bucket = _RATE.get(ip, [])
    bucket = [t for t in bucket if now - t < window]
    if len(bucket) >= limit:
        retry_after = int(window - (now - bucket[0])) + 1
        raise HTTPException(
            status_code=429,
            detail="Too many requests. Please try again later.",
            headers={"Retry-After": str(retry_after)},
        )
    bucket.append(now)
    _RATE[ip] = bucket


def _sanitize(text: str) -> str:
    """Strip HTML entities and trim whitespace."""
    return html.escape(text.strip(), quote=True)


def _verify_admin(credentials: HTTPBasicCredentials = Depends(security)) -> None:
    """Verify admin credentials with bcrypt (preferred) or plaintext fallback."""
    user_ok = secrets.compare_digest(
        credentials.username.encode("utf8"),
        settings.ADMIN_USER.encode("utf8"),
    )

    if settings.ADMIN_PASS_HASH:
        pass_ok = bcrypt.verify(credentials.password, settings.ADMIN_PASS_HASH)
    else:
        if settings.APP_ENV == "production":
            log.warning(
                "Using plaintext ADMIN_PASS in production — set ADMIN_PASS_HASH instead!"
            )
        pass_ok = secrets.compare_digest(
            credentials.password.encode("utf8"),
            settings.ADMIN_PASS.encode("utf8"),
        )

    if not (user_ok and pass_ok):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized",
            headers={"WWW-Authenticate": "Basic"},
        )


def _validate_origin(request: Request) -> None:
    """Validate POST request origin to prevent cross-site request forgery.

    Permits:
      1. Requests with no Origin header (direct / server-to-server).
      2. Same-origin requests matching request.base_url or Host/Forwarded headers.
      3. Wildcard origins if "*" in settings.CORS_ORIGINS.
      4. Origins explicitly listed in settings.CORS_ORIGINS.
      5. Any local loopback origin when APP_ENV == "development".
    """
    origin = request.headers.get("origin")
    if not origin:
        return

    origin_clean = origin.rstrip("/")

    # 1. Allow same-origin requests (e.g. frontend served by this backend)
    server_origin = str(request.base_url).rstrip("/")
    if origin_clean == server_origin:
        return

    host = request.headers.get("x-forwarded-host") or request.headers.get("host")
    if host:
        proto = request.headers.get("x-forwarded-proto") or request.url.scheme
        if origin_clean == f"{proto}://{host}":
            return

    # 2. Allow wildcard
    if "*" in settings.CORS_ORIGINS:
        return

    # 3. Allow explicitly listed CORS origins
    allowed_origins = {o.rstrip("/") for o in settings.CORS_ORIGINS}
    if origin_clean in allowed_origins or origin in settings.CORS_ORIGINS:
        return

    # 4. In development mode, allow any localhost/loopback port
    if settings.APP_ENV == "development" and DEV_ORIGIN_RE.match(origin_clean):
        return

    log.warning(
        "Rejected request from unallowed origin: %s (allowed: %s, server: %s)",
        origin,
        settings.CORS_ORIGINS,
        server_origin,
    )
    raise HTTPException(status_code=403, detail="Origin not allowed.")


def _generate_csrf_token() -> str:
    """Generate a signed CSRF token."""
    return csrf_serializer.dumps(secrets.token_hex(16))


def _validate_csrf_token(request: Request) -> None:
    """Validate the CSRF token from the X-CSRF-Token header against the cookie."""
    cookie_token = request.cookies.get("csrf_token")
    header_token = request.headers.get("x-csrf-token")

    if not cookie_token or not header_token:
        raise HTTPException(status_code=403, detail="Missing CSRF token.")

    if cookie_token != header_token:
        raise HTTPException(status_code=403, detail="Invalid CSRF token.")

    # Verify the token signature and expiry
    try:
        csrf_serializer.loads(header_token, max_age=CSRF_MAX_AGE)
    except BadSignature:
        raise HTTPException(status_code=403, detail="Invalid or expired CSRF token.")


# ── Lifespan ─────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown hooks.  Gracefully handle DB init failures so the
    serverless function can still boot (lazy init in db.py is the fallback)."""
    try:
        init_db()
    except Exception:
        pass  # DB will be lazily initialised on first request via _get_collection()
    yield
    close_db()


# ── Application ──────────────────────────────────────────────────────────────

app = FastAPI(
    title="Crimson Nyx Studios Backend",
    version="3.0.0",
    lifespan=lifespan,
)

# ── Middleware ───────────────────────────────────────────────────────────────

cors_options = {
    "allow_origins": settings.CORS_ORIGINS,
    "allow_credentials": True,
    "allow_methods": ["GET", "POST", "OPTIONS"],
    "allow_headers": ["Content-Type", "Authorization", "X-CSRF-Token"],
}
if settings.APP_ENV == "development":
    cors_options["allow_origin_regex"] = r"^https?://(localhost|127\.0\.0\.1|\[::1\])(:\d+)?$"

app.add_middleware(CORSMiddleware, **cors_options)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    """Attach security headers to every response."""
    response = await call_next(request)

    # Content-Security-Policy — no unsafe-eval in production
    csp_parts = [
        "default-src 'self'",
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com",
        "font-src 'self' https://fonts.gstatic.com",
        "img-src 'self' data:",
        "media-src 'self'",
        "connect-src 'self'",
        "script-src 'self' 'unsafe-inline'",
        "frame-ancestors 'none'",
        "base-uri 'self'",
        "form-action 'self'",
    ]
    response.headers["Content-Security-Policy"] = "; ".join(csp_parts)

    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Strict-Transport-Security"] = (
        "max-age=31536000; includeSubDomains"
    )
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["X-Permitted-Cross-Domain-Policies"] = "none"
    response.headers["Permissions-Policy"] = (
        "camera=(), microphone=(), geolocation=(), payment=()"
    )
    return response


@app.middleware("http")
async def limit_body_size(request: Request, call_next):
    """Reject requests whose body exceeds MAX_BODY_SIZE."""
    content_length = request.headers.get("content-length")
    if content_length and int(content_length) > settings.MAX_BODY_SIZE:
        return JSONResponse(
            {"detail": "Request body too large."},
            status_code=413,
        )
    return await call_next(request)


# ── API Routes ───────────────────────────────────────────────────────────────

@app.get("/api/csrf-token")
async def get_csrf_token() -> JSONResponse:
    """Issue a CSRF token — returned in the JSON body and set as a cookie."""
    token = _generate_csrf_token()
    response = JSONResponse({"csrf_token": token})
    response.set_cookie(
        key="csrf_token",
        value=token,
        httponly=False,       # JS needs to read this
        secure=settings.APP_ENV == "production",
        samesite="strict",
        max_age=CSRF_MAX_AGE,
        path="/",
    )
    return response


@app.post("/api/contact")
async def submit_contact(payload: ContactPayload, request: Request) -> JSONResponse:
    """Accept a contact-form submission."""
    _validate_origin(request)
    _validate_csrf_token(request)
    ip = _get_client_ip(request)
    _rate_limit(ip)

    if payload.company:
        raise HTTPException(status_code=400, detail="Invalid submission.")

    name = _sanitize(payload.name)
    email = payload.email.strip().lower()
    service = payload.service.strip()
    message = _sanitize(payload.message)

    if not EMAIL_RE.match(email):
        raise HTTPException(status_code=400, detail="Please enter a valid email address.")

    if service not in ALLOWED_SERVICES:
        raise HTTPException(status_code=400, detail="Please choose a valid service.")

    created_at = datetime.now(timezone.utc).isoformat()
    user_agent = request.headers.get("user-agent")

    message_id = insert_message(
        created_at=created_at,
        ip=None if ip == "unknown" else ip,
        user_agent=user_agent,
        name=name,
        email=email,
        service=service,
        message=message,
    )

    # Fire-and-forget email notification
    send_contact_email(name=name, email=email, service=service, message=message)

    return JSONResponse({"ok": True, "id": message_id})


@app.get("/health")
def health() -> JSONResponse:
    """Health check including MongoDB status."""
    return JSONResponse({"ok": True, **db_health()})


@app.get("/favicon.ico")
def favicon() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "cnslogo1.png", media_type="image/png")


# ── Admin Routes ─────────────────────────────────────────────────────────────

@app.get("/admin")
def admin_page(_: None = Depends(_verify_admin)) -> FileResponse:
    return FileResponse(ADMIN_PAGE)


@app.get("/api/admin/messages")
def admin_messages(
    limit: int = Query(200, ge=1, le=500),
    offset: int = Query(0, ge=0),
    _: None = Depends(_verify_admin),
) -> JSONResponse:
    return JSONResponse(
        {"ok": True, "messages": list_messages(limit=limit, offset=offset)}
    )


# ── Page Routes (clean URLs) ────────────────────────────────────────────────

@app.get("/")
def root() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "index.html")


@app.get("/services")
def services_page() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "services.html")


@app.get("/work")
def work_page() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "work.html")


@app.get("/about")
def about_page() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "about.html")


@app.get("/contact")
def contact_page() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "contact.html")


# Serve the entire frontend folder (html, images, etc.)
app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")
