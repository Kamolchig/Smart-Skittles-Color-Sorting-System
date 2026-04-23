import csv
import io
import sqlite3
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

from .config import settings


class DatabaseManager:
    _instance = None
    _class_lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._class_lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, "_initialized"):
            self.db_path = Path(settings.DB_PATH)
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            self._write_lock = threading.Lock()
            self._init_db()
            self._initialized = True

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        return conn

    def _init_db(self):
        with self._write_lock:
            with self._connect() as conn:
                conn.executescript(
                    """
                    CREATE TABLE IF NOT EXISTS detections (
                        id          INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp   TEXT    NOT NULL,
                        color       TEXT    NOT NULL,
                        confidence  REAL    NOT NULL,
                        sensor_id   TEXT    DEFAULT 'TCS34725',
                        raw_payload TEXT,
                        source      TEXT    DEFAULT 'serial'
                    );

                    CREATE TABLE IF NOT EXISTS system_events (
                        id          INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp   TEXT    NOT NULL,
                        event_type  TEXT    NOT NULL,
                        message     TEXT    NOT NULL,
                        severity    TEXT    DEFAULT 'info'
                    );

                    CREATE INDEX IF NOT EXISTS idx_det_ts    ON detections(timestamp);
                    CREATE INDEX IF NOT EXISTS idx_det_color ON detections(color);
                    CREATE INDEX IF NOT EXISTS idx_evt_ts    ON system_events(timestamp);
                    """
                )

    # ------------------------------------------------------------------
    # Detections
    # ------------------------------------------------------------------

    def add_detection(
        self,
        color: str,
        confidence: float,
        sensor_id: str = "TCS34725",
        raw_payload: str = "",
        source: str = "serial",
    ) -> int:
        ts = datetime.utcnow().isoformat()
        with self._write_lock:
            with self._connect() as conn:
                cur = conn.execute(
                    """
                    INSERT INTO detections (timestamp, color, confidence, sensor_id, raw_payload, source)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (ts, color, confidence, sensor_id, raw_payload, source),
                )
                return cur.lastrowid

    def get_latest_detection(self) -> Optional[Dict]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM detections ORDER BY id DESC LIMIT 1"
            ).fetchone()
            return dict(row) if row else None

    def get_recent_detections(self, limit: int = 50) -> List[Dict]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM detections ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()
            return [dict(r) for r in rows]

    def get_total_count(self) -> int:
        with self._connect() as conn:
            return conn.execute("SELECT COUNT(*) FROM detections").fetchone()[0]

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    def get_color_stats(self) -> Dict:
        with self._connect() as conn:
            total = conn.execute("SELECT COUNT(*) FROM detections").fetchone()[0]
            rows = conn.execute(
                """
                SELECT color,
                       COUNT(*)        AS count,
                       AVG(confidence) AS avg_conf
                FROM detections
                GROUP BY color
                ORDER BY count DESC
                """
            ).fetchall()

        by_color: Dict[str, Dict] = {}
        for r in rows:
            by_color[r["color"]] = {
                "count": r["count"],
                "percentage": round(r["count"] / total * 100, 1) if total > 0 else 0.0,
                "avg_confidence": round(r["avg_conf"] or 0.0, 3),
            }
        return {"total": total, "by_color": by_color}

    def get_rate_stats(self, minutes: int = 5) -> Dict:
        since_n = (datetime.utcnow() - timedelta(minutes=minutes)).isoformat()
        since_1 = (datetime.utcnow() - timedelta(minutes=1)).isoformat()
        with self._connect() as conn:
            count_n = conn.execute(
                "SELECT COUNT(*) FROM detections WHERE timestamp > ?", (since_n,)
            ).fetchone()[0]
            count_1 = conn.execute(
                "SELECT COUNT(*) FROM detections WHERE timestamp > ?", (since_1,)
            ).fetchone()[0]

        per_min = round(count_n / minutes, 2) if minutes else 0.0
        per_sec = round(count_1 / 60, 3)
        return {
            f"candies_last_{minutes}min": count_n,
            "per_minute": per_min,
            "per_second": per_sec,
            "window_minutes": minutes,
            "count_last_1min": count_1,
        }

    def get_time_series(self, hours: int = 1) -> List[Dict]:
        since = (datetime.utcnow() - timedelta(hours=hours)).isoformat()
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT timestamp, color, confidence, source
                FROM detections
                WHERE timestamp > ?
                ORDER BY timestamp ASC
                """,
                (since,),
            ).fetchall()
        return [dict(r) for r in rows]

    def get_throughput_series(self, minutes: int = 15) -> List[Dict]:
        since = (datetime.utcnow() - timedelta(minutes=minutes)).isoformat()
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT strftime('%Y-%m-%dT%H:%M:00', timestamp) AS minute,
                       COUNT(*) AS count
                FROM detections
                WHERE timestamp > ?
                GROUP BY minute
                ORDER BY minute ASC
                """,
                (since,),
            ).fetchall()
        return [dict(r) for r in rows]

    def get_confidence_by_color(self) -> List[Dict]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT color, confidence FROM detections ORDER BY id DESC LIMIT 500"
            ).fetchall()
        return [dict(r) for r in rows]

    # ------------------------------------------------------------------
    # System events
    # ------------------------------------------------------------------

    def add_system_event(self, event_type: str, message: str, severity: str = "info"):
        ts = datetime.utcnow().isoformat()
        with self._write_lock:
            with self._connect() as conn:
                conn.execute(
                    """
                    INSERT INTO system_events (timestamp, event_type, message, severity)
                    VALUES (?, ?, ?, ?)
                    """,
                    (ts, event_type, message, severity),
                )

    def get_system_events(self, limit: int = 20) -> List[Dict]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM system_events ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()
        return [dict(r) for r in rows]

    # ------------------------------------------------------------------
    # Maintenance
    # ------------------------------------------------------------------

    def clear_all(self):
        with self._write_lock:
            with self._connect() as conn:
                conn.execute("DELETE FROM detections")
                conn.execute("DELETE FROM system_events")

    def export_csv(self) -> str:
        with self._connect() as conn:
            rows = conn.execute("SELECT * FROM detections ORDER BY id ASC").fetchall()
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(["id", "timestamp", "color", "confidence", "sensor_id", "raw_payload", "source"])
        for r in rows:
            writer.writerow(list(dict(r).values()))
        return buf.getvalue()


db = DatabaseManager()
