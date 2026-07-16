"""ForEvi API entrypoint.

Security posture:
- All data flows through this API; the frontend is a pure client.
- Strict CORS, security headers on every response, structured logging.
- JWT bearer auth, role based access control, hash chained audit log.
- Realtime case and user events over an authenticated WebSocket.
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import auth, cases, health, notifications, users, ws
from app.core.config import get_settings
from app.core.events import start_redis_bridge
from app.core.logging import configure_logging, logger
from app.db.base import Base, engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await start_redis_bridge()
    logger.info("forevi api started", extra={"action": "startup"})
    yield
    await engine.dispose()


settings = get_settings()
app = FastAPI(
    title="ForEvi API",
    description="Agentic AI based investigation of UFDR using cross modal evidence correlation",
    version="0.2.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    return response


p = settings.api_v1_prefix
app.include_router(health.router, prefix=p)
app.include_router(auth.router, prefix=p)
app.include_router(users.router, prefix=p)
app.include_router(cases.router, prefix=p)
app.include_router(notifications.router, prefix=p)
app.include_router(ws.router, prefix=p)
