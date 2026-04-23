import json
import logging
import threading
import time
from typing import Optional

try:
    import serial
    SERIAL_AVAILABLE = True
except ImportError:
    SERIAL_AVAILABLE = False

from .database import db

logger = logging.getLogger(__name__)

VALID_COLORS = {"red", "green", "blue", "yellow", "orange", "purple", "unknown"}


def _parse_payload(line: str) -> Optional[dict]:
    """Accept JSON or CSV (color,confidence[,sensor_id]) line."""
    line = line.strip()
    if not line:
        return None

    # --- JSON ---
    if line.startswith("{"):
        try:
            data = json.loads(line)
            color = str(data.get("color", "unknown")).lower()
            confidence = float(data.get("confidence", 0.9))
            sensor_id = str(data.get("sensor_id", "TCS34725"))
            return {
                "color": color if color in VALID_COLORS else "unknown",
                "confidence": max(0.0, min(1.0, confidence)),
                "sensor_id": sensor_id,
                "raw_payload": line,
            }
        except (json.JSONDecodeError, ValueError):
            pass

    # --- CSV ---
    parts = [p.strip() for p in line.split(",")]
    if len(parts) >= 2:
        try:
            color = parts[0].lower()
            confidence = float(parts[1])
            sensor_id = parts[2] if len(parts) > 2 else "TCS34725"
            return {
                "color": color if color in VALID_COLORS else "unknown",
                "confidence": max(0.0, min(1.0, confidence)),
                "sensor_id": sensor_id,
                "raw_payload": line,
            }
        except (ValueError, IndexError):
            pass

    logger.debug("Unrecognised serial line: %s", line[:80])
    return None


class SerialReader:
    def __init__(self):
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._running = False
        self.port: Optional[str] = None
        self.baud_rate: int = 9600
        self._ser = None

    @property
    def is_running(self) -> bool:
        return self._running

    def start(self, port: str, baud_rate: int = 9600) -> bool:
        if not SERIAL_AVAILABLE:
            logger.error("pyserial is not installed")
            return False
        if self._running:
            self.stop()
        self.port = port
        self.baud_rate = baud_rate
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._read_loop, name="SerialReader", daemon=True)
        self._thread.start()
        time.sleep(0.8)
        return self._running

    def stop(self):
        self._stop_event.set()
        if self._ser:
            try:
                self._ser.close()
            except Exception:
                pass
        self._running = False

    def _read_loop(self):
        try:
            self._ser = serial.Serial(self.port, self.baud_rate, timeout=1)
            self._running = True
            db.add_system_event(
                "serial_connect",
                f"Connected to {self.port} @ {self.baud_rate} baud",
                "info",
            )
            logger.info("Serial connected: %s", self.port)

            while not self._stop_event.is_set():
                try:
                    if self._ser.in_waiting:
                        raw = self._ser.readline()
                        line = raw.decode("utf-8", errors="ignore").strip()
                        if line:
                            det = _parse_payload(line)
                            if det:
                                db.add_detection(
                                    color=det["color"],
                                    confidence=det["confidence"],
                                    sensor_id=det["sensor_id"],
                                    raw_payload=det["raw_payload"],
                                    source="serial",
                                )
                    else:
                        time.sleep(0.01)
                except Exception as exc:
                    logger.error("Serial read error: %s", exc)
                    time.sleep(0.5)

        except Exception as exc:
            logger.error("Serial connection failed: %s", exc)
            db.add_system_event("serial_error", str(exc), "critical")
        finally:
            self._running = False
            if self._ser:
                try:
                    self._ser.close()
                except Exception:
                    pass
            db.add_system_event("serial_disconnect", f"Disconnected from {self.port}", "warning")
            logger.info("Serial reader stopped")


serial_reader = SerialReader()
