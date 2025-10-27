# app/main.py
# NOTE: DATABASE_URL fix is now in app/__init__.py (runs automatically on package import)
from . import social, gps, screentime, family, subscription, test_endpoints, test_users
from fastapi import FastAPI, Request, HTTPException
from .admin import execute_sql
from fastapi.middleware.cors import CORSMiddleware
from fastapi.concurrency import run_in_threadpool
from sqlalchemy import create_engine, text
from . import payment_gateway, ai_assistant, invoice_generator, ai_assistant_enhanced, ai_assistant_enhanced_v2, ai_assistant_intelligent, public_content
from .admin import employee_exemptions
# NEW IMPORTS - Add after existing imports
from .admin import payroll, profit_loss, infra_costs
from . import websockets, call_recordings, scam_cases, digital_arrest, auto_alert, kyc_verification, live_alerts, subscription_enhanced, voice_biometric, scam_prediction, community_reports, email_webhook_v2 as email_webhook
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
    """psycopg accepts postgresql:// ; strip any +driver suffix."""
    return (
        raw.replace("postgresql+psycopg://", "postgresql://")
        .replace("postgresql+asyncpg://", "postgresql://")
    )


def make_app():
    s = get_settings()
    app = FastAPI(title="EchoFort API", version="1.0.0")

    # -------------------------------------------------------------
    # CORS
    # -------------------------------------------------------------
    origins = [o.strip() for o in s.ALLOW_ORIGINS.split(",")] if s.ALLOW_ORIGINS else ["*"]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ------------------------------------------------------------
    # Boot mode & Engine
    # ------------------------------------------------------------
    boot_mode = (s.APP_BOOT_MODE or "full").lower().strip()
    engine = None

    if boot_mode != "bare":
        # Build a psycopg SQLAlchemy URL
        db_url = s.DATABASE_URL
        if db_url.startswith("postgresql://"):
            db_url = db_url.replace("postgresql://", "postgresql+psycopg://", 1)

        # Reliable sync engine
        engine = create_engine(db_url, pool_pre_ping=True, future=True)

        # Idempotent migrations at build/start time
        def _apply():
            base = Path(__file__).resolve().parents[1]
            mdir = base / "migrations"
            for fname in ["001_init.sql", "002_rbac.sql", "003_social_time.sql", "004_new_features.sql", "014_employees_table.sql", "009-complete-reset.sql", "010_missing_tables.sql", "011_ai_pending_tasks.sql", "012_payment_gateway_management.sql", "013_auto_alerts_enhanced.sql", "015_vault_and_exemptions.sql", "015_youtube_and_scam_alerts.sql"]:
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

    # ------------------------------------------------------------
    # DB shim so routes can await request.app.state.db.execute(...)
    # ------------------------------------------------------------
    class DBShim:
        def __init__(self, _engine):
            self._engine = _engine

        async def execute(self, clause, params=None):
            if self._engine is None:
                # If someone calls DB in bare mode, fail clearly
                raise RuntimeError("DB not initialized (APP_BOOT_MODE=bare)")
            def _exec():
                with self._engine.begin() as conn:
                    return conn.execute(clause, params or {})
            return await run_in_threadpool(_exec)

    @app.on_event("startup")
    async def startup():
        # Attach the db handle (exists even in bare mode, but will raise if used)
        app.state.db = DBShim(engine)

    # ------------------------------------------------------------
    # Routers
    # ------------------------------------------------------------
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
    # NEW ROUTERS
    app.include_router(gps.router)
    app.include_router(screentime.router)
    app.include_router(family.router)
    app.include_router(subscription.router)
    app.include_router(test_endpoints.router)
    app.include_router(payment_gateway.router)
    app.include_router(ai_assistant.router)
    app.include_router(ai_assistant_enhanced.router)
    app.include_router(ai_assistant_enhanced_v2.router)
    app.include_router(ai_assistant_intelligent.router)
    app.include_router(public_content.router)
    app.include_router(public_content.router_public)  # Legacy /public routes for frontend
    app.include_router(employee_exemptions.router)
    # NEW ROUTERS - Add after existing include_router calls
    app.include_router(payroll.router)
    app.include_router(profit_loss.router)
    app.include_router(infra_costs.router)
    app.include_router(websockets.router)
    # Note: ai_assistant.router already exists, just replace the file
    app.include_router(invoice_generator.router)
    app.include_router(execute_sql.router)
    # NEW ROUTERS - Critical APIs
    app.include_router(call_recordings.router)
    app.include_router(scam_cases.router)
    app.include_router(digital_arrest.router)
    app.include_router(auto_alert.router)
    app.include_router(kyc_verification.router)
    app.include_router(live_alerts.router)
    app.include_router(subscription_enhanced.router)
    app.include_router(voice_biometric.router)
    app.include_router(scam_prediction.router)
    app.include_router(community_reports.router)
    app.include_router(test_users.router)
    app.include_router(email_webhook.router)



    # ------------------------------------------------------------
    # Admin: run migrations via psycopg (GET/POST)
    # ------------------------------------------------------------
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
                    for fname in ["001_init.sql", "002_rbac.sql", "003_social_time.sql", "004_new_features.sql", "014_employees_table.sql", "009-complete-reset.sql", "010_missing_tables.sql", "011_ai_pending_tasks.sql", "012_payment_gateway_management.sql", "013_auto_alerts_enhanced.sql", "015_vault_and_exemptions.sql", "015_youtube_and_scam_alerts.sql"]:
                        sql = (mdir / fname).read_text(encoding="utf-8")
                        cur.execute(sql)
                conn.commit()
        except Exception as e:
            raise HTTPException(500, f"Migration failed: {e}")
        return {"ok": True}

    # ------------------------------------------------------------
    # Health
    # ------------------------------------------------------------
    @app.get("/health")
    async def health():
        if engine is None:
            # bare boot — app is up, DB intentionally not initialized
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

# Payment Gateway Manager (Super Admin)
from . import payment_gateway_manager
app.include_router(payment_gateway_manager.router)

# Auto-Alert V2 (Global with Evidence & Certificate)
from . import auto_alert_v2
app.include_router(auto_alert_v2.router)

# Import unified auth and employee management
from .auth import unified_login, simple_login, fixed_auth
from .admin import employee_management as emp_mgmt

# Register unified auth router
app.include_router(unified_login.router)

# Register fixed auth router (backup)
app.include_router(fixed_auth.router)

# Register employee management router
app.include_router(emp_mgmt.router)

# WhatsApp/SMS Protection
from . import whatsapp_sms_protection
app.include_router(whatsapp_sms_protection.router)

# Complaint Filing System
from . import complaint_filing
app.include_router(complaint_filing.router)

# Evidence Vault
from . import evidence_vault
app.include_router(evidence_vault.router)

# Caller ID System
from . import caller_id
app.include_router(caller_id.router)

# Call Recording Vault (Super Admin)
from .admin import call_recording_vault
app.include_router(call_recording_vault.router)

# Super Admin Vault (CLASSIFIED)
from .admin import super_admin_vault
app.include_router(super_admin_vault.router)

# Customer Exemptions (Super Admin)
from .admin import customer_exemptions
app.include_router(customer_exemptions.router)

# Super Admin Initialization (One-time use)
from .admin import initialize_super_admin, dashboard_stats, service_integrations
app.include_router(initialize_super_admin.router, prefix="/auth", tags=["Super Admin Init"])
app.include_router(simple_login.router)
app.include_router(dashboard_stats.router)
app.include_router(service_integrations.router)

# Support Ticket Management (Employee Dashboard)
from . import support_management
app.include_router(support_management.router)

# WhatsApp Support Integration
from . import whatsapp_support
app.include_router(whatsapp_support.router)

# Admin Approvals
from . import admin_approvals
app.include_router(admin_approvals.router)

# Call Analysis with Whisper API (Simplified Version)
from . import whisper_analysis
app.include_router(whisper_analysis.router)
