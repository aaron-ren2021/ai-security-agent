from __future__ import annotations

import os
from pathlib import Path
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from flask import Flask
import uvicorn

from src.core.testing import attach_test_client
from src.models.auth import User, db
import src.models.palo  # noqa: F401  # ensure Palo Alto models are registered
from src.routers import auth_router, file_router, rag_router
from src.routers.ag_ui_router import router as ag_ui_router
from src.routers.pydantic_ai_router import router as pydantic_ai_router
from src.routers.postgres_search_router import router as postgres_search_router
from src.services.auth_service import AuthService, get_request_info

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"


def _build_flask_backend() -> Flask:
    flask_app = Flask("ai-security-agent-db")
    flask_app.config.setdefault("SECRET_KEY", os.getenv("FLASK_SECRET_KEY", "asdf#FGSgvasgf$5$WGT"))
    flask_app.config.setdefault("SQLALCHEMY_DATABASE_URI", os.getenv("DATABASE_URL", "sqlite:///app.db"))
    flask_app.config.setdefault("SQLALCHEMY_TRACK_MODIFICATIONS", False)
    flask_app.config.setdefault("TESTING", False)
    db.init_app(flask_app)
    return flask_app


class FlaskCompatFastAPI(FastAPI):
    """FastAPI subclass that exposes key Flask-style helpers used in tests."""

    def __init__(self, flask_app: Flask, **kwargs):
        super().__init__(**kwargs)
        self._flask_app = flask_app
        self.config = flask_app.config

    def app_context(self):
        return self._flask_app.app_context()

    @property
    def testing(self):
        return self._flask_app.testing

    @testing.setter
    def testing(self, value: bool):
        self._flask_app.testing = value
        self.config["TESTING"] = value


flask_backend = _build_flask_backend()
app = FlaskCompatFastAPI(
    flask_backend,
    title="AI Security Agent",
    version="2.0.0",
)
app.secret_key = app.config["SECRET_KEY"]  # type: ignore[attr-defined]
app.static_folder = str(STATIC_DIR)
attach_test_client(app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

app.include_router(rag_router.router)
app.include_router(auth_router.router)
app.include_router(file_router.router)
app.include_router(ag_ui_router)
app.include_router(pydantic_ai_router)
app.include_router(postgres_search_router)

_db_context = None


@app.on_event("startup")
async def _startup_db():
    global _db_context
    if _db_context is None:
        _db_context = app.app_context()
        _db_context.push()
    with app.app_context():
        db.create_all()


def init_database():
    """Convenience helper to create tables from scripts."""
    with app.app_context():
        db.create_all()


auth_service = AuthService()


@app.get("/health")
async def health_check():
    return {"status": "ok", "framework": "fastapi", "database": app.config.get("SQLALCHEMY_DATABASE_URI")}


@app.get("/test-login")
async def test_login(request: Request):
    user = User.query.filter_by(email="test@example.com").first()
    if not user:
        user = User(
            name="測試用戶",
            email="test@example.com",
            provider="test",
            provider_id="test123",
        )
        db.session.add(user)
        db.session.commit()
    request_info = get_request_info(request)
    session_id = auth_service.create_user_session(user, request_info)
    response = RedirectResponse(url="/", status_code=302)
    secure_cookie = request.url.scheme == "https"
    response.set_cookie(
        "session_id",
        session_id,
        max_age=86400,
        httponly=True,
        secure=secure_cookie,
        samesite="lax",
    )
    return response


def _static_file(path: Path) -> FileResponse:
    if not path.exists():
        raise HTTPException(status_code=404, detail="Static asset not found")
    return FileResponse(path)


@app.get("/login")
async def login_page():
    return _static_file(STATIC_DIR / "login.html")


def _resolve_app_entry(request: Request) -> Path:
    session_id = request.cookies.get("session_id")
    if session_id:
        return STATIC_DIR / "index.html"
    return STATIC_DIR / "login.html"


@app.get("/")
async def serve_root(request: Request):
    return _static_file(_resolve_app_entry(request))


@app.get("/{full_path:path}")
async def serve_static_or_spa(full_path: str, request: Request):
    if full_path:
        candidate = STATIC_DIR / full_path
        if candidate.exists() and candidate.is_file():
            return _static_file(candidate)
    if full_path in {"", "index", "index.html", "app", "dashboard"}:
        return _static_file(_resolve_app_entry(request))
    fallback = STATIC_DIR / "index.html"
    if not fallback.exists():
        raise HTTPException(status_code=404, detail="SPA entry not found")
    return FileResponse(fallback)


if __name__ == "__main__":
    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", "5002")),
        reload=True,
    )
