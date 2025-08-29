# app/logging.py
from __future__ import annotations
import json, logging, os, sys, time
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Dict

_DEFAULT_EXCLUDE = {
    "args","asctime","created","exc_info","exc_text","filename","funcName","levelname",
    "levelno","lineno","module","msecs","message","msg","name","pathname","process",
    "processName","relativeCreated","stack_info","thread","threadName"
}

class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        base: Dict[str, Any] = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        # include JSON-serializable extras
        for k, v in record.__dict__.items():
            if k in _DEFAULT_EXCLUDE:
                continue
            try:
                json.dumps(v)
                base[k] = v
            except Exception:
                base[k] = str(v)
        if record.exc_info:
            base["exc"] = self.formatException(record.exc_info)
        return json.dumps(base, ensure_ascii=False)

def init_logging(level: str | None = None) -> logging.Logger:
    lvl = (level or os.getenv("LOG_LEVEL", "INFO")).upper()
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    logging.basicConfig(handlers=[handler], level=getattr(logging, lvl, logging.INFO), force=True)
    # quiet overly verbose libraries if desired
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.error").setLevel(logging.INFO)
    return logging.getLogger("app")

def get_logger(name: str = "app") -> logging.Logger:
    return logging.getLogger(name)

@contextmanager
def stage(name: str, **fields: Any):
    """Time a pipeline stage and emit start/ok/error JSON logs."""
    log = get_logger(f"stage.{name}")
    t0 = time.perf_counter()
    log.info("start", extra={"stage": name, **fields})
    try:
        yield
    except Exception:
        dt = int((time.perf_counter() - t0) * 1000)
        log.exception("error", extra={"stage": name, "duration_ms": dt, **fields})
        raise
    else:
        dt = int((time.perf_counter() - t0) * 1000)
        log.info("ok", extra={"stage": name, "duration_ms": dt, **fields})