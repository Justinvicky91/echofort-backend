# app/main.py
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.concurrency import run_in_threadpool
from sqlalchemy import create_engine, text
from pathlib import Path
import os
import psycopg

from .deps import get_settings
from .auth import otp, device
from .ai import voice, image
from .billing import razorpay_webhooks, stripe_webhooks
from .admin import audit, supervoice, marketing, employees, privacy, export as export_csv
from . import social

def pg_dsn_for_psycopg(raw: str) -> str:
    # psycopg accepts postgresql://; strip any +driver
    return raw.replace("postgresql+psycopg://", "postgresql://")\
              .replace("postgresql+asyncpg://", "postgresql://")

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

    # ---------- boot modes ----------
    boot_mode = (s.APP_BOOT_MODE or "full").lower().strip()
    engine = None

    if boot_mode != "bare":
        # Use sync engine (most reliable on Railway)
        db_url = s.DATABASE_URL
        if db_url.startswith("postgresql://"):
            db_url = db_url.replace("postgresql://", "postgresql+psycopg://", 1)
        engine = create_engine(db_url, pool_pre_ping=True, future=True)

        # Auto-migrate on boot (idempotent)
        def _apply():
            base = Path(__file__).resolve().parents[1]
            mdir = base / "migrations"
            for fname in ["001_init.sql", "002_rbac.sql", "003_social_time.sql"]:
                sql = (mdir / fname).read_text(encoding="utf-8")
                with engine.begin() as conn:
                    conn.exec_driver_sql(sql)
        try:
            _apply()
            print("Auto-migrations applied.")
        except Exception as e:
            print("Auto-migrate skipped:", e)
    else:
        print("Booting in BARE mode: skipping DB init on startup")

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

    # One-time admin migration endpoint (GET/POST) secured by MIGRATE_KEY, using psycopg directly
    @app.api_route("/admin/run-migrations", methods=["GET", "POST"])
    async def run_migrations(request: Request, key: str):
        token = os.getenv("MIGRATE_KEY")
        if not token or key != token:
            raise HTTPException(status_code=403, detail="Bad token")
        dsn = pg_dsn_for_psycopg(os.getenv("DATABASE_URL", ""))
        if not dsn:
            raise HTTPException(500, "DATABASE_URL missing")
        base = Path(__file__).resolve().parents[1]
        mdir = base / "migrations"
        try:
            with psycopg.connect(dsn) as conn:
                with conn.cursor() as cur:
                    for fname in ["001_init.sql", "002_rbac.sql", "003_social_time.sql"]:
                        sql = (mdir / fname).read_text(encoding="utf-8")
                        cur.execute(sql)
                conn.commit()
        except Exception as e:
            raise HTTPException(500, f"Migration failed: {e}")
        return {"ok": True}

    @app.get("/health")
    async def health():
        if engine is None:
            # bare boot — app is up, DB not initialized yet
            return {"status": "ok", "db": None, "env": s.APP_ENV, "mode": "bare"}
        try:
            def _ping():
                with engine.connect() as conn:
                    conn.execute(text("SELECT 1"))
            await run_in_threadpool(_ping)
            db_ok = True
        except Exception:
            db_ok = False
        return {"status": "ok", "db": db_ok, "env": s.APP_ENV, "mode": "full"}

    return app

app = make_app()
