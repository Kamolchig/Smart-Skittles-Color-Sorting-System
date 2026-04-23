#!/usr/bin/env python
"""
simulate_serial.py — Feed synthetic candy detections into the running backend.

Modes:
  1. REST API mode (default) — posts directly to FastAPI. No hardware needed.
  2. Serial port mode         — writes JSON lines to a real/virtual COM port.

Usage:
    python scripts/simulate_serial.py                   # API mode, 1 candy/s
    python scripts/simulate_serial.py --rate 3          # API mode, 3 candy/s
    python scripts/simulate_serial.py --port COM4       # write to serial port
    python scripts/simulate_serial.py --port /dev/pts/1 --rate 2

Requirements for serial port mode on Windows: com0com (virtual serial port pair)
Requirements for serial port mode on Linux/Mac: socat
    socat -d -d pty,raw,echo=0 pty,raw,echo=0
"""

import argparse
import json
import random
import sys
import time
from datetime import datetime

import requests

API_URL = "http://127.0.0.1:8000"

COLORS   = ["red", "orange", "yellow", "green", "purple"]
WEIGHTS  = [0.22, 0.20, 0.21, 0.21, 0.16]


def _generate() -> dict:
    if random.random() < 0.03:
        return {
            "color": "unknown",
            "confidence": round(random.uniform(0.25, 0.55), 3),
            "sensor_id": "TCS34725",
            "timestamp": datetime.utcnow().isoformat(),
        }
    return {
        "color": random.choices(COLORS, weights=WEIGHTS)[0],
        "confidence": round(random.uniform(0.78, 0.99), 3),
        "sensor_id": "TCS34725",
        "timestamp": datetime.utcnow().isoformat(),
    }


def _run_api(rate: float):
    interval = 1.0 / rate
    count = 0
    print(f"[API mode] Sending to {API_URL}  ({rate} candy/s) — Ctrl+C to stop\n")
    while True:
        det = _generate()
        try:
            r = requests.post(f"{API_URL}/detections/add", json=det, timeout=2)
            status = "✓" if r.ok else "✗"
        except Exception as exc:
            status = f"✗ {exc}"
        count += 1
        print(f"[{count:>5}]  {status}  {det['color'].upper():<8}  {det['confidence']:.0%}")
        time.sleep(interval)


def _run_serial(port: str, baud: int, rate: float):
    try:
        import serial
    except ImportError:
        print("pyserial is not installed. Run: pip install pyserial")
        sys.exit(1)

    interval = 1.0 / rate
    count = 0
    print(f"[Serial mode] Writing to {port} @ {baud} baud  ({rate} candy/s)\n")
    with serial.Serial(port, baud, timeout=1) as ser:
        while True:
            det = _generate()
            line = json.dumps(det) + "\n"
            ser.write(line.encode())
            count += 1
            print(f"[{count:>5}]  → {line.strip()}")
            time.sleep(interval)


def main():
    p = argparse.ArgumentParser(description="Simulate serial candy detections")
    p.add_argument("--port",  default=None, help="COM port (omit = REST API mode)")
    p.add_argument("--baud",  type=int, default=9600)
    p.add_argument("--rate",  type=float, default=1.0, help="Candies per second")
    args = p.parse_args()

    try:
        if args.port:
            _run_serial(args.port, args.baud, args.rate)
        else:
            _run_api(args.rate)
    except KeyboardInterrupt:
        print("\nSimulation stopped.")


if __name__ == "__main__":
    main()
