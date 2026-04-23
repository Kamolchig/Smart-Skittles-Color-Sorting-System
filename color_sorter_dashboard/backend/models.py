from typing import Dict, Optional
from pydantic import BaseModel, Field


class DetectionIn(BaseModel):
    color: str
    confidence: float = Field(ge=0.0, le=1.0)
    sensor_id: str = "TCS34725"
    timestamp: Optional[str] = None


class DetectionOut(BaseModel):
    id: int
    timestamp: str
    color: str
    confidence: float
    sensor_id: str
    raw_payload: Optional[str] = None
    source: str


class ColorStats(BaseModel):
    count: int
    percentage: float
    avg_confidence: float


class StatsResponse(BaseModel):
    total: int
    by_color: Dict[str, ColorStats]


class RateResponse(BaseModel):
    per_minute: float
    per_second: float
    window_minutes: int
    count_last_1min: int


class Alert(BaseModel):
    id: str
    severity: str
    title: str
    message: str
    timestamp: str


class SerialConfig(BaseModel):
    port: str
    baud_rate: int = 9600


class SimulationConfig(BaseModel):
    rate: float = Field(default=1.5, ge=0.1, le=20.0)


class HealthResponse(BaseModel):
    status: str
    mode: str
    serial_port: Optional[str]
    simulation_active: bool
    serial_active: bool
    total_detections: int
    uptime_seconds: float
