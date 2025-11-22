"""
EchoFort Production Monitoring with Sentry
Error tracking, performance monitoring, and alerting
"""

import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
from sentry_sdk.integrations.redis import RedisIntegration
import os

def init_sentry():
    """Initialize Sentry for error tracking and performance monitoring"""
    
    sentry_dsn = os.getenv("SENTRY_DSN")
    environment = os.getenv("ENVIRONMENT", "production")
    release = os.getenv("RELEASE_VERSION", "1.0.0")
    
    if not sentry_dsn:
        print("⚠️  Sentry DSN not configured. Error tracking disabled.")
        return
    
    sentry_sdk.init(
        dsn=sentry_dsn,
        environment=environment,
        release=f"echofort-backend@{release}",
        
        # Integrations
        integrations=[
            FastApiIntegration(transaction_style="endpoint"),
            SqlalchemyIntegration(),
            RedisIntegration(),
        ],
        
        # Performance monitoring
        traces_sample_rate=0.1,  # 10% of transactions
        profiles_sample_rate=0.1,  # 10% profiling
        
        # Error sampling
        sample_rate=1.0,  # 100% of errors
        
        # Additional options
        send_default_pii=False,  # DPDP compliance
        attach_stacktrace=True,
        max_breadcrumbs=50,
        
        # Before send hook for filtering
        before_send=before_send_hook,
        
        # Before breadcrumb hook
        before_breadcrumb=before_breadcrumb_hook,
    )
    
    print(f"✅ Sentry initialized for {environment} environment")


def before_send_hook(event, hint):
    """Filter and modify events before sending to Sentry"""
    
    # Don't send health check errors
    if "health" in event.get("request", {}).get("url", ""):
        return None
    
    # Don't send 404 errors for known paths
    if event.get("status_code") == 404:
        return None
    
    # Add custom tags
    event["tags"] = event.get("tags", {})
    event["tags"]["platform"] = "backend"
    event["tags"]["service"] = "echofort-api"
    
    # Add user context (without PII)
    if "user" in event:
        user = event["user"]
        # Remove PII fields
        user.pop("email", None)
        user.pop("phone", None)
        user.pop("ip_address", None)
    
    return event


def before_breadcrumb_hook(crumb, hint):
    """Filter breadcrumbs before adding to event"""
    
    # Don't log sensitive data
    if crumb.get("category") == "query":
        # Sanitize SQL queries
        if "data" in crumb:
            crumb["data"] = sanitize_sql(crumb["data"])
    
    return crumb


def sanitize_sql(data):
    """Remove sensitive data from SQL queries"""
    # Basic sanitization - remove potential PII
    sensitive_fields = ["password", "phone", "email", "otp", "token"]
    
    if isinstance(data, dict):
        return {
            k: "***" if any(field in k.lower() for field in sensitive_fields) else v
            for k, v in data.items()
        }
    
    return data


# Custom error tracking functions

def capture_api_error(error, context=None):
    """Capture API errors with context"""
    with sentry_sdk.push_scope() as scope:
        if context:
            for key, value in context.items():
                scope.set_context(key, value)
        
        sentry_sdk.capture_exception(error)


def capture_payment_error(error, payment_data):
    """Capture payment-related errors"""
    with sentry_sdk.push_scope() as scope:
        scope.set_tag("error_type", "payment")
        scope.set_context("payment", {
            "gateway": payment_data.get("gateway"),
            "amount": payment_data.get("amount"),
            "currency": payment_data.get("currency"),
            "plan": payment_data.get("plan"),
        })
        sentry_sdk.capture_exception(error)


def capture_ai_error(error, ai_context):
    """Capture AI-related errors"""
    with sentry_sdk.push_scope() as scope:
        scope.set_tag("error_type", "ai")
        scope.set_context("ai", {
            "model": ai_context.get("model"),
            "operation": ai_context.get("operation"),
            "input_size": ai_context.get("input_size"),
        })
        sentry_sdk.capture_exception(error)


def capture_database_error(error, query_info):
    """Capture database errors"""
    with sentry_sdk.push_scope() as scope:
        scope.set_tag("error_type", "database")
        scope.set_context("database", {
            "operation": query_info.get("operation"),
            "table": query_info.get("table"),
        })
        sentry_sdk.capture_exception(error)


# Performance monitoring

def start_transaction(name, op="http.server"):
    """Start a performance transaction"""
    return sentry_sdk.start_transaction(name=name, op=op)


def add_breadcrumb(message, category="info", level="info", data=None):
    """Add a breadcrumb for debugging"""
    sentry_sdk.add_breadcrumb(
        message=message,
        category=category,
        level=level,
        data=data or {}
    )


# User context

def set_user_context(user_id, username=None):
    """Set user context for error tracking (without PII)"""
    sentry_sdk.set_user({
        "id": user_id,
        "username": username,
    })


def clear_user_context():
    """Clear user context"""
    sentry_sdk.set_user(None)


# Custom metrics

def record_metric(metric_name, value, unit="none", tags=None):
    """Record custom metrics"""
    sentry_sdk.metrics.incr(
        metric_name,
        value=value,
        unit=unit,
        tags=tags or {}
    )
