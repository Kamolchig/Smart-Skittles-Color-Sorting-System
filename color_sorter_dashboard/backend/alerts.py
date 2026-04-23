from datetime import datetime, timedelta
from typing import List, Dict

from .database import db

_T = {
    "no_data_warn": 10,
    "no_data_crit": 30,
    "unknown_warn": 10.0,
    "unknown_crit": 25.0,
    "conf_warn": 0.70,
    "conf_crit": 0.50,
    "imbalance_gap": 8.0,
    "throughput_warn": 0.15,
}


def get_alerts() -> List[Dict]:
    alerts: List[Dict] = []
    now = datetime.utcnow()

    # ── No-data alerts ────────────────────────────────────────────────
    latest = db.get_latest_detection()
    if latest:
        try:
            ts = datetime.fromisoformat(latest["timestamp"])
            age = (now - ts).total_seconds()
            if age > _T["no_data_crit"]:
                alerts.append(
                    _alert(
                        "no_data_crit",
                        "critical",
                        "No Data Received",
                        f"Sensor silent for {int(age)}s — check connection.",
                    )
                )
            elif age > _T["no_data_warn"]:
                alerts.append(
                    _alert(
                        "no_data_warn",
                        "warning",
                        "Data Delay",
                        f"No detection for {int(age)} seconds.",
                    )
                )
        except Exception:
            pass
    else:
        alerts.append(
            _alert(
                "awaiting",
                "info",
                "Awaiting First Detection",
                "Start simulation or connect hardware to begin.",
            )
        )

    stats = db.get_color_stats()
    total = stats["total"]
    by_color = stats["by_color"]

    if total > 20:
        # ── Unknown rate ──────────────────────────────────────────────
        unk_pct = by_color.get("unknown", {}).get("percentage", 0.0)
        if unk_pct >= _T["unknown_crit"]:
            alerts.append(
                _alert(
                    "high_unk_crit",
                    "critical",
                    "High Unknown Rate",
                    f"{unk_pct:.1f}% unknown — sensor needs calibration.",
                )
            )
        elif unk_pct >= _T["unknown_warn"]:
            alerts.append(
                _alert(
                    "high_unk_warn",
                    "warning",
                    "Elevated Unknown Rate",
                    f"{unk_pct:.1f}% of detections are unclassified.",
                )
            )

        # ── Confidence ───────────────────────────────────────────────
        conf_rows = db.get_confidence_by_color()
        if conf_rows:
            recent = [r["confidence"] for r in conf_rows[:100]]
            avg_conf = sum(recent) / len(recent)
            if avg_conf < _T["conf_crit"]:
                alerts.append(
                    _alert(
                        "conf_crit",
                        "critical",
                        "Very Low Confidence",
                        f"Avg confidence {avg_conf:.1%} — sensor misaligned?",
                    )
                )
            elif avg_conf < _T["conf_warn"]:
                alerts.append(
                    _alert(
                        "conf_warn",
                        "warning",
                        "Low Detection Confidence",
                        f"Average confidence: {avg_conf:.1%}.",
                    )
                )

        # ── Color imbalance ──────────────────────────────────────────
        main = {k: v for k, v in by_color.items() if k != "unknown"}
        if len(main) >= 3:
            avg_pct = sum(v["percentage"] for v in main.values()) / len(main)
            for color, data in main.items():
                if (
                    data["percentage"] < (avg_pct - _T["imbalance_gap"])
                    and data["percentage"] < 12.0
                ):
                    alerts.append(
                        _alert(
                            f"low_{color}",
                            "info",
                            f"Low {color.title()} Count",
                            f"{data['count']} {color} candies ({data['percentage']:.1f}%) — below average.",
                        )
                    )

    # ── Throughput ────────────────────────────────────────────────────
    if total > 10:
        rate = db.get_rate_stats(minutes=2)
        if rate["per_second"] < _T["throughput_warn"]:
            alerts.append(
                _alert(
                    "low_throughput",
                    "warning",
                    "Low Throughput",
                    f"Only {rate['per_second']:.2f} candy/s in the last 2 minutes.",
                )
            )

    return alerts[:10]


def _alert(aid: str, severity: str, title: str, message: str) -> Dict:
    return {
        "id": aid,
        "severity": severity,
        "title": title,
        "message": message,
        "timestamp": datetime.utcnow().isoformat(),
    }
