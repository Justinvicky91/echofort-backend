# app/main.py
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.concurrency import run_in_threadpool

from sqlalchemy import create_engine, text
from pathlib import Path
import os

from .deps import get_settings
from .auth import otp, device
from .ai import voice, image
from .billing import razorpay_webhooks, stripe_webhooks
from .admin import audit, supervoice, marketing, employees, privacy, export as export_csv
from . import social

def make_app():
    s = get_settings()
    app = FastAPI(title="EchoFort API", version="1.0.0")

    # CORS
    origins = [o.strip() for o in s.ALLOW_ORIGINS.split(",")] if s.ALLOW_ORIGINS else ["*"]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ---- build sync engine; force psycopg driver prefix if needed ----
    db_url = s.DATABASE_URL
    if db_url.startswith("postgresql+asyncpg://"):
        db_url = db_url.replace("postgresql+asyncpg://", "postgresql+psycopg://", 1)
    elif db_url.startswith("postgresql://"):
        db_url = db_url.replace("postgresql://", "postgresql+psycopg://", 1)

    engine = create_engine(db_url, pool_pre_ping=True, future=True)

    # Small async shim so existing code can keep using: await db.execute(text(...))
    class AsyncDB:
        def __init__(self, _engine):
            self._engine = _engine

        async def execute(self, clause, params=None):
            def _exec():
                with self._engine.begin() as conn:
                    return conn.execute(clause, params or {})
            return await run_in_threadpool(_exec)

    @app.on_event("startup")
    async def startup():
        app.state.db = AsyncDB(engine)

        # ---- auto-migrate on boot (idempotent) ----
        def _apply():
            base = Path(__file__).resolve().parents[1]  # repo root
            mdir = base / "migrations"
            for fname in ["001_init.sql", "002_rbac.sql", "003_social_time.sql"]:
                sql = (mdir / fname).read_text(encoding="utf-8")
                with engine.begin() as conn:
                    conn.exec_driver_sql(sql)
        try:
            await run_in_threadpool(_apply)
            print("Auto-migrations applied.")
        except Exception as e:
            print("Auto-migrate skipped:", e)

    @app.on_event("shutdown")
    async def shutdown():
        # nothing to close: engine uses pool
        pass

    # --------- routes ---------
    app.include_router(otp.router)
    app.include_router(device.router)
    app.include_router(voice.router)
    app.include_router(image.router)
    app.include_router(razorpay_webhooks.router)
    app.include_router(stripe_webhooks.router)
    app.include_router(audit.router)
    app.include_router(supervoice.router)
    app.include_router(marketing.router)
    app.include_router(employees.router)
    app.include_router(privacy.router)
    app.include_router(export_csv.router)
    app.include_router(social.router)

    # One-time admin migration endpoint (GET/POST) secured by MIGRATE_KEY
    @app.api_route("/admin/run-migrations", methods=["GET", "POST"])
    async def run_migrations(request: Request, key: str):
        token = os.getenv("MIGRATE_KEY")
        if not token or key != token:
            raise HTTPException(status_code=403, detail="Bad token")

        def _apply():
            base = Path(__file__).resolve().parents[1]
            mdir = base / "migrations"
            for fname in ["001_init.sql", "002_rbac.sql", "003_social_time.sql"]:
                sql = (mdir / fname).read_text(encoding="utf-8")
                with engine.begin() as conn:
                    conn.exec_driver_sql(sql)
        await run_in_threadpool(_apply)
        return {"ok": True}

    @app.get("/health")
    async def health():
        try:
            def _ping():
                with engine.connect() as conn:
                    conn.execute(text("SELECT 1"))
            await run_in_threadpool(_ping)
            db_ok = True
        except Exception:
            db_ok = False
        return {"status": "ok", "db": db_ok, "env": s.APP_ENV}

    return app

app = make_app()