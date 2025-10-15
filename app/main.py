# app/main.py
from fastapi import FastAPI, Request, HTTPException
import os
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import text
from pathlib import Path

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

    # ---- DB URL ensure psycopg driver ----
    db_url = s.DATABASE_URL
    if db_url.startswith("postgresql://"):
        db_url = db_url.replace("postgresql://", "postgresql+psycopg://", 1)

    engine = create_async_engine(db_url, echo=False, future=True)
    Session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    @app.on_event("startup")
    async def startup():
        app.state.db = Session()
        # ---- auto-migrate on boot (001–003) ----
        try:
            base = Path(__file__).resolve().parents[1]  # repo root (backend/)
            mdir = base / "migrations"
            for fname in ["001_init.sql", "002_rbac.sql", "003_social_time.sql"]:
                sql = (mdir / fname).read_text(encoding="utf-8")
                async with engine.begin() as conn:
                    await conn.exec_driver_sql(sql)
            print("Auto-migrations applied.")
        except Exception as e:
            print("Auto-migrate skipped:", e)

    @app.on_event("shutdown")
    async def shutdown():
        await app.state.db.close()

    # Routes
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

    @app.get("/health")
    async def health():
        try:
            await app.state.db.execute(text("SELECT 1"))
            db_ok = True
        except Exception:
            db_ok = False
        return {"status": "ok", "db": db_ok, "env": s.APP_ENV}

# ---- one-time manual migration trigger (secure with token) ----
    @app.post("/admin/run-migrations")
    async def run_migrations(key: str, request: Request):
        if key != os.getenv("MIGRATE_KEY"):
            raise HTTPException(status_code=403, detail="Bad token")
        base = Path(__file__).resolve().parents[1]  # repo root
        mdir = base / "migrations"
        for fname in ["001_init.sql", "002_rbac.sql", "003_social_time.sql"]:
            sql = (mdir / fname).read_text(encoding="utf-8")
            async with engine.begin() as conn:
                await conn.exec_driver_sql(sql)
        return {"ok": True}
    return app

app = make_app()
