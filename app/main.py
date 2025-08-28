from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator

app = FastAPI(title="RAG API")

@app.get("/healthz")
def healthz():
    return {"ok": True}

# Prometheus /metrics
Instrumentator().instrument(app).expose(app, endpoint="/metrics")