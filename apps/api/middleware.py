"""
middleware.py — Tenant-aware and Audit middleware for the ScopeSentinel API (Epic 5.1.2, 5.3.2)

TenantMiddleware: Reads X-Tenant-Id from request headers → request.state.tenant_id
AuditMiddleware:  Publishes fire-and-forget audit events to Redpanda on mutating calls
"""

import json
import os
from typing import Optional

import structlog
from aiokafka import AIOKafkaProducer
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = structlog.get_logger(__name__)

REDPANDA_BROKERS = os.environ.get("REDPANDA_BROKERS", "localhost:19092")

# Routes that should bypass tenant checking (global / admin paths)
TENANT_EXEMPT_PATHS = {
    "/",
    "/health",
    "/docs",
    "/redoc",
    "/openapi.json",
}

# HTTP methods that produce audit events
AUDIT_METHODS = {"POST", "PATCH", "PUT", "DELETE"}


class TenantMiddleware(BaseHTTPMiddleware):
    """
    Extracts X-Tenant-Id from the incoming request header and stores it
    in request.state.tenant_id so downstream DB sessions can set search_path.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        org_id = request.headers.get("X-ScopeSentinel-Org-ID")
        if org_id:
            request.state.tenant_id = org_id.replace("-", "_")
        else:
            request.state.tenant_id = None

        response = await call_next(request)
        return response


class AuditMiddleware(BaseHTTPMiddleware):
    """
    After every mutating API call (POST/PATCH/PUT/DELETE), publishes an audit
    event to `t.{org_id}.audit` Redpanda topic (fire-and-forget, non-blocking).

    The audit service consumer picks these up and writes them to `audit_events`.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)

        if request.method in AUDIT_METHODS and response.status_code < 400:
            # Build the event asynchronously without blocking the response
            try:
                org_id = getattr(request.state, "tenant_id", None) or "global"
                user_id = getattr(request.state, "user_id", None)
                event = {
                    "org_id": org_id,
                    "user_id": user_id,
                    "action": f"{request.method.lower()}:{request.url.path}",
                    "resource_type": _infer_resource_type(request.url.path),
                    "resource_id": None,
                    "payload": {
                        "method": request.method,
                        "path": str(request.url.path),
                        "status_code": response.status_code,
                    },
                }
                topic = f"t.{org_id}.audit"
                # Send without awaiting — fire-and-forget via background task
                import asyncio
                asyncio.create_task(_publish_audit_event(topic, event))
            except Exception as exc:
                logger.warning("audit_middleware.publish_failed", error=str(exc))

        return response


def _infer_resource_type(path: str) -> Optional[str]:
    """Infer resource type from the URL path."""
    segments = [s for s in path.split("/") if s]
    if len(segments) >= 2 and segments[0] == "api":
        return segments[1]  # e.g., "runs", "workflows", "users"
    return None


async def _publish_audit_event(topic: str, event: dict) -> None:
    """Publish a single audit event to Redpanda."""
    try:
        producer = AIOKafkaProducer(bootstrap_servers=REDPANDA_BROKERS)
        await producer.start()
        try:
            await producer.send_and_wait(topic, json.dumps(event).encode("utf-8"))
        finally:
            await producer.stop()
    except Exception as exc:
        logger.debug("audit_middleware.redpanda_unavailable", error=str(exc))

