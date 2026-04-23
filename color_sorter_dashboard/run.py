#!/usr/bin/env python
"""
Entry point — starts the FastAPI backend in a background thread,
then launches the Dash dashboard in the main thread.

Usage:
    python run.py                     # simulation mode (default)
    python run.py --no-sim            # disable auto-simulation
    python run.py --port COM4         # custom serial port
    python run.py --rate 2.0          # simulation rate (candy/s)
"""

import argparse
import logging
import os
import sys
import threading
import time

import requests
import uvicorn

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
)
logger = logging.getLogger("run")


def _parse_args():
    p = argparse.ArgumentParser(description="Smart Skittles Dashboard")
    p.add_argument("--no-sim",       action="store_true", help="Disable auto-simulation")
    p.add_argument("--port",         default=None,        help="Serial port (e.g. COM3)")
    p.add_argument("--rate",         type=float,          default=None,
                   help="Simulation rate in candy/s")
    p.add_argument("--api-port",     type=int,            default=8000)
    p.add_argument("--dash-port",    type=int,            default=8050)
    return p.parse_args()


def _apply_args(args):
    if args.no_sim:
        os.environ.setdefault("SIMULATION_MODE", "false")
    if args.rate:
        os.environ["SIMULATION_RATE"] = str(args.rate)
    if args.port:
        os.environ["SERIAL_PORT"] = args.port


def _wait_for_api(host: str, port: int, retries: int = 20):
    url = f"http://{host}:{port}/health"
    for _ in range(retries):
        try:
            r = requests.get(url, timeout=1)
            if r.ok:
                return True
        except Exception:
            pass
        time.sleep(0.5)
    return False


def _run_backend(host: str, port: int):
    uvicorn.run(
        "backend.main:app",
        host=host,
        port=port,
        log_level="warning",
        access_log=False,
    )


def main():
    args = _parse_args()
    _apply_args(args)

    api_host = "0.0.0.0"
    api_port = args.api_port
    dash_host = "0.0.0.0"
    dash_port = args.dash_port

    # ── Start backend ──────────────────────────────────────────────────────
    logger.info("Starting FastAPI backend on port %d …", api_port)
    backend_thread = threading.Thread(
        target=_run_backend,
        args=(api_host, api_port),
        name="FastAPI",
        daemon=True,
    )
    backend_thread.start()

    logger.info("Waiting for backend to become ready …")
    if not _wait_for_api("127.0.0.1", api_port):
        logger.error("Backend did not start in time. Exiting.")
        sys.exit(1)
    logger.info("Backend ready ✓")

    # ── Start dashboard ────────────────────────────────────────────────────
    logger.info(
        "Launching Dash dashboard → http://127.0.0.1:%d", dash_port
    )
    from dashboard.app import create_app

    app = create_app()
    app.run(
        host=dash_host,
        port=dash_port,
        debug=False,
        use_reloader=False,
    )


if __name__ == "__main__":
    main()
