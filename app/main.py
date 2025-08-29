from fastapi import FastAPI
from contextlib import asynccontextmanager
from prometheus_fastapi_instrumentator import Instrumentator
from app.logging import init_logging
from app.api.routes import ingest_router, search_router, health_router
from app.search.opensearch_client import client as opensearch_client
from app.search.index_setup import ensure_index_and_alias

logger = init_logging()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize resources on startup, cleanup on shutdown."""
    # Startup
    try:
        ensure_index_and_alias(opensearch_client)
        logger.info("startup_complete")
    except Exception as e:
        logger.error("startup_failed", extra={"error": str(e)})
        # Don't prevent startup, but log the error
    
    yield
    
    # Shutdown (if needed)
    logger.info("shutdown_complete")

app = FastAPI(title="RAG API", lifespan=lifespan)

# Include routers
app.include_router(ingest_router)
app.include_router(search_router)
app.include_router(health_router)

@app.get("/healthz")
def healthz():
    return {"ok": True}

# Prometheus /metrics
Instrumentator().instrument(app).expose(app, endpoint="/metrics")