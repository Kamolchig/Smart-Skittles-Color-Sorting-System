import json
import logging
import random
import threading
from datetime import datetime
from typing import Optional

from .database import db

logger = logging.getLogger(__name__)

_COLORS = ["red", "orange", "yellow", "green", "purple"]
_WEIGHTS = [0.22, 0.20, 0.21, 0.21, 0.16]


class Simulator:
    def __init__(self):
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._running = False
        self.rate: float = 1.5
        self._generated: int = 0

    @property
    def is_running(self) -> bool:
        return self._running

    def start(self, rate: float = 1.5):
        if self._running:
            self.rate = max(0.1, min(20.0, rate))
            return
        self.rate = max(0.1, min(20.0, rate))
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._loop, name="Simulator", daemon=True
        )
        self._thread.start()
        db.add_system_event(
            "simulation_start", f"Simulation started at {self.rate} candy/s", "info"
        )
        logger.info("Simulation started at %.2f candy/s", self.rate)

    def stop(self):
        if not self._running:
            return
        self._stop_event.set()
        self._running = False
        db.add_system_event("simulation_stop", "Simulation stopped by user", "info")
        logger.info("Simulation stopped")

    def set_rate(self, rate: float):
        self.rate = max(0.1, min(20.0, rate))

    # ------------------------------------------------------------------

    def _loop(self):
        self._running = True
        try:
            while not self._stop_event.is_set():
                self._emit()
                interval = 1.0 / self.rate
                jitter = random.uniform(-0.05, 0.05) * interval
                self._stop_event.wait(timeout=max(0.05, interval + jitter))
        finally:
            self._running = False

    def _emit(self):
        if random.random() < 0.03:
            color = "unknown"
            confidence = round(random.uniform(0.25, 0.55), 3)
        else:
            color = random.choices(_COLORS, weights=_WEIGHTS)[0]
            confidence = round(random.uniform(0.78, 0.99), 3)

        payload = json.dumps(
            {
                "color": color,
                "confidence": confidence,
                "sensor_id": "TCS34725",
                "timestamp": datetime.utcnow().isoformat(),
            }
        )
        db.add_detection(
            color=color,
            confidence=confidence,
            sensor_id="TCS34725",
            raw_payload=payload,
            source="simulation",
        )
        self._generated += 1


simulator = Simulator()
