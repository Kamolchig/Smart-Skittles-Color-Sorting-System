import logging
import time
from contextlib import asynccontextmanager
from typing import List, Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse

from .alerts import get_alerts
from .config import settings
from .database import db
from .models import (
    Alert,
    DetectionIn,
    DetectionOut,
    HealthResponse,
    SerialConfig,
    SimulationConfig,
)
from .serial_reader import serial_reader
from .simulator import simulator

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)
_START_TIME = time.time()


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.add_system_event("api_start", "FastAPI backend started", "info")
    if settings.SIMULATION_MODE:
        simulator.start(settings.SIMULATION_RATE)
        logger.info("Auto-started simulation at %.2f candy/s", settings.SIMULATION_RATE)
    yield
    simulator.stop()
    serial_reader.stop()
    db.add_system_event("api_stop", "FastAPI backend stopped", "info")


app = FastAPI(
    title="Smart Skittles API",
    description="Backend for the Smart Skittles Color Sorting System",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ══════════════════════════════════════════════════════════════════════
# Health
# ══════════════════════════════════════════════════════════════════════

@app.get("/health", response_model=HealthResponse, tags=["System"])
def health():
    if simulator.is_running:
        mode = "simulation"
    elif serial_reader.is_running:
        mode = "serial"
    else:
        mode = "idle"
    return {
        "status": "ok",
        "mode": mode,
        "serial_port": serial_reader.port,
        "simulation_active": simulator.is_running,
        "serial_active": serial_reader.is_running,
        "total_detections": db.get_total_count(),
        "uptime_seconds": round(time.time() - _START_TIME, 1),
    }


# ══════════════════════════════════════════════════════════════════════
# Detections
# ══════════════════════════════════════════════════════════════════════

@app.get("/detections/latest", response_model=Optional[DetectionOut], tags=["Detections"])
def get_latest():
    return db.get_latest_detection()


@app.get("/detections/recent", response_model=List[DetectionOut], tags=["Detections"])
def get_recent(limit: int = Query(default=50, le=500)):
    return db.get_recent_detections(limit)


@app.post("/detections/add", tags=["Detections"])
def add_detection(detection: DetectionIn):
    """Manually inject a detection (used by simulate_serial.py)."""
    import json

    raw = json.dumps(detection.model_dump())
    row_id = db.add_detection(
        color=detection.color,
        confidence=detection.confidence,
        sensor_id=detection.sensor_id,
        raw_payload=raw,
        source="external",
    )
    return {"id": row_id, "status": "ok"}


# ══════════════════════════════════════════════════════════════════════
# Stats
# ══════════════════════════════════════════════════════════════════════

@app.get("/stats/summary", tags=["Stats"])
def stats_summary():
    return db.get_color_stats()


@app.get("/stats/rate", tags=["Stats"])
def stats_rate(minutes: int = Query(default=5, le=60)):
    return db.get_rate_stats(minutes)


@app.get("/stats/timeseries", tags=["Stats"])
def stats_timeseries(hours: int = Query(default=1, le=24)):
    return db.get_time_series(hours)


@app.get("/stats/throughput", tags=["Stats"])
def stats_throughput(minutes: int = Query(default=15, le=60)):
    return db.get_throughput_series(minutes)


@app.get("/stats/confidence", tags=["Stats"])
def stats_confidence():
    return db.get_confidence_by_color()


# ══════════════════════════════════════════════════════════════════════
# Alerts
# ══════════════════════════════════════════════════════════════════════

@app.get("/alerts", response_model=List[Alert], tags=["Alerts"])
def alerts():
    return get_alerts()


# ══════════════════════════════════════════════════════════════════════
# Serial
# ══════════════════════════════════════════════════════════════════════

@app.get("/config/serial", tags=["Serial"])
def get_serial_config():
    return {
        "port": serial_reader.port or settings.SERIAL_PORT,
        "baud_rate": serial_reader.baud_rate,
        "connected": serial_reader.is_running,
    }


@app.post("/config/serial", tags=["Serial"])
def set_serial_config(config: SerialConfig):
    serial_reader.stop()
    ok = serial_reader.start(config.port, config.baud_rate)
    if not ok:
        raise HTTPException(status_code=400, detail=f"Cannot connect to {config.port}")
    return {"status": "connected", "port": config.port}


@app.post("/serial/stop", tags=["Serial"])
def stop_serial():
    serial_reader.stop()
    return {"status": "stopped"}


# ══════════════════════════════════════════════════════════════════════
# Simulation
# ══════════════════════════════════════════════════════════════════════

@app.post("/simulation/start", tags=["Simulation"])
def start_simulation(config: SimulationConfig = SimulationConfig()):
    simulator.start(config.rate)
    return {"status": "started", "rate": simulator.rate}


@app.post("/simulation/stop", tags=["Simulation"])
def stop_simulation():
    simulator.stop()
    return {"status": "stopped"}


@app.post("/simulation/rate", tags=["Simulation"])
def set_rate(config: SimulationConfig):
    simulator.set_rate(config.rate)
    return {"rate": simulator.rate}


# ══════════════════════════════════════════════════════════════════════
# Data management
# ══════════════════════════════════════════════════════════════════════

@app.delete("/data/clear", tags=["Data"])
def clear_data():
    db.clear_all()
    db.add_system_event("data_cleared", "All data cleared by operator", "warning")
    return {"status": "cleared"}


@app.get("/data/export", response_class=PlainTextResponse, tags=["Data"])
def export_csv():
    csv_data = db.export_csv()
    return PlainTextResponse(
        content=csv_data,
        headers={"Content-Disposition": "attachment; filename=skittles_detections.csv"},
    )


@app.get("/events", tags=["System"])
def get_events(limit: int = Query(default=20, le=100)):
    return db.get_system_events(limit)
