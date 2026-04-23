"""All Dash callbacks — real-time updates and control actions."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

import plotly.graph_objects as go
import requests
from dash import Input, Output, State, callback, ctx, dcc, html, no_update

from .layout import CANDY

logger = logging.getLogger(__name__)

API = "http://127.0.0.1:8000"
_TIMEOUT = 3

# ── Chart base style ───────────────────────────────────────────────────────────
_CHART = dict(
    paper_bgcolor="#161b22",
    plot_bgcolor="#0d1117",
    font=dict(color="#8b949e", family="Segoe UI, sans-serif", size=11),
    margin=dict(l=44, r=16, t=28, b=36),
    xaxis=dict(gridcolor="#21262d", linecolor="#30363d", zeroline=False),
    yaxis=dict(gridcolor="#21262d", linecolor="#30363d", zeroline=False),
    legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(size=11)),
    hoverlabel=dict(bgcolor="#21262d", bordercolor="#30363d",
                    font=dict(color="#f0f6ff", size=12)),
)


def _api(path: str, **kwargs) -> dict | list | None:
    try:
        r = requests.get(f"{API}{path}", timeout=_TIMEOUT, **kwargs)
        if r.ok:
            return r.json()
    except Exception:
        pass
    return None


def _post(path: str, **kwargs) -> dict | None:
    try:
        r = requests.post(f"{API}{path}", timeout=_TIMEOUT, **kwargs)
        if r.ok:
            return r.json()
    except Exception:
        pass
    return None


def _del(path: str) -> dict | None:
    try:
        r = requests.delete(f"{API}{path}", timeout=_TIMEOUT)
        if r.ok:
            return r.json()
    except Exception:
        pass
    return None


def _age_str(ts: str) -> str:
    try:
        dt = datetime.fromisoformat(ts)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        delta = (datetime.now(timezone.utc) - dt).total_seconds()
        if delta < 2:
            return "just now"
        if delta < 60:
            return f"{int(delta)}s ago"
        if delta < 3600:
            return f"{int(delta/60)}m ago"
        return f"{int(delta/3600)}h ago"
    except Exception:
        return "—"


def _color_hex(color: str) -> str:
    return CANDY.get(color, CANDY["unknown"])["hex"]


def _empty_fig(msg: str = "No data") -> go.Figure:
    fig = go.Figure()
    fig.update_layout(
        **_CHART,
        annotations=[dict(text=msg, x=0.5, y=0.5, xref="paper", yref="paper",
                          showarrow=False, font=dict(color="#6e7681", size=13))],
    )
    return fig


# ══════════════════════════════════════════════════════════════════════════════
# 1-second tick — hero card
# ══════════════════════════════════════════════════════════════════════════════

def register_callbacks(app):

    @app.callback(
        Output("hero-card",       "style"),
        Output("hero-orb",        "style"),
        Output("hero-orb",        "children"),
        Output("hero-name",       "children"),
        Output("hero-conf-text",  "children"),
        Output("hero-conf-bar",   "style"),
        Output("hero-timestamp",  "children"),
        Input("tick-1s", "n_intervals"),
    )
    def update_hero(_):
        det = _api("/detections/latest")
        if not det:
            return (
                {"--hero-glow": "transparent"},
                {"background": "#21262d", "boxShadow": "none",
                 "width": "130px", "height": "130px", "borderRadius": "50%",
                 "display": "flex", "alignItems": "center", "justifyContent": "center",
                 "fontSize": "52px", "margin": "0 auto 18px", "position": "relative",
                 "zIndex": 1},
                "?",
                "—", "—",
                {"width": "0%"},
                "Waiting for first detection…",
            )

        color = det.get("color", "unknown")
        conf = det.get("confidence", 0.0)
        meta = CANDY.get(color, CANDY["unknown"])
        ts_raw = det.get("timestamp", "")
        ts_fmt = ts_raw[:19].replace("T", "  ") if ts_raw else "—"
        conf_pct = f"{conf:.1%}"
        conf_w = f"{conf * 100:.1f}%"

        card_style = {
            "--hero-glow": meta["glow"],
            "borderColor": meta["hex"],
            "boxShadow": f"0 0 30px {meta['glow']}",
        }
        orb_style = {
            "background": f"radial-gradient(circle at 35% 35%, {meta['hex']}dd, {meta['hex']}88)",
            "boxShadow": f"0 0 50px {meta['glow']}, inset 0 0 20px rgba(255,255,255,0.1)",
            "width": "130px", "height": "130px", "borderRadius": "50%",
            "display": "flex", "alignItems": "center", "justifyContent": "center",
            "fontSize": "52px", "margin": "0 auto 18px",
            "position": "relative", "zIndex": 1,
            "--orb-border": meta["hex"],
        }
        return (
            card_style,
            orb_style,
            meta["icon"],
            color.upper(),
            conf_pct,
            {"width": conf_w},
            f"🕐  {ts_fmt}  UTC",
        )

    # ══════════════════════════════════════════════════════════════════════════
    # 2-second tick — header, status, performance, distribution, bar, table
    # ══════════════════════════════════════════════════════════════════════════

    @app.callback(
        # Header
        Output("hdr-status-badge", "children"),
        Output("hdr-mode-badge",   "children"),
        Output("hdr-uptime",       "children"),
        # Status panel
        Output("st-mode",  "children"),
        Output("st-port",  "children"),
        Output("st-baud",  "children"),
        Output("st-last",  "children"),
        Output("st-age",   "children"),
        Output("st-total", "children"),
        # Performance
        Output("perf-per-sec",  "children"),
        Output("perf-per-min",  "children"),
        Output("perf-5min",     "children"),
        Output("perf-1min",     "children"),
        Output("perf-total",    "children"),
        Input("tick-2s", "n_intervals"),
    )
    def update_status_and_perf(_):
        health = _api("/health")
        rate   = _api("/stats/rate?minutes=5")

        # ── Defaults ──
        hdr_status = html.Span([html.Span(className="live-dot me-1"), "OFFLINE"],
                               className="badge-pill badge-offline")
        hdr_mode   = html.Span("IDLE", className="badge-pill badge-idle")
        hdr_uptime = "uptime: —"
        st_mode = st_port = st_baud = st_last = st_age = st_total = "—"
        p_sec = p_min = p_5min = p_1min = p_total = "—"

        if health:
            sim_on  = health.get("simulation_active", False)
            ser_on  = health.get("serial_active", False)
            mode    = health.get("mode", "idle")
            total   = health.get("total_detections", 0)
            uptime  = health.get("uptime_seconds", 0)
            port    = health.get("serial_port") or "—"

            hdr_status = html.Span(
                [html.Span(className="live-dot me-1"), "ONLINE"],
                className="badge-pill badge-online",
            )
            hdr_mode = (
                html.Span("● SIMULATION", className="badge-pill badge-sim")
                if sim_on else
                html.Span("● SERIAL", className="badge-pill badge-serial")
                if ser_on else
                html.Span("IDLE", className="badge-pill badge-idle")
            )
            h, m, s = int(uptime // 3600), int((uptime % 3600) // 60), int(uptime % 60)
            hdr_uptime = f"uptime {h:02d}:{m:02d}:{s:02d}"

            st_mode  = mode.capitalize()
            st_port  = port
            st_baud  = "9600" if not ser_on else "—"
            st_total = f"{total:,}"

        latest = _api("/detections/latest")
        if latest:
            ts = latest.get("timestamp", "")
            st_last = ts[:19].replace("T", " ") if ts else "—"
            st_age  = _age_str(ts)
        else:
            st_last = st_age = "—"

        if rate:
            p_sec   = f"{rate.get('per_second', 0):.2f}"
            p_min   = f"{rate.get('per_minute', 0):.1f}"
            p_5min  = str(rate.get("candies_last_5min", 0))
            p_1min  = str(rate.get("count_last_1min", 0))

        stats = _api("/stats/summary")
        if stats:
            total_det = stats.get("total", 0)
            p_total   = f"{total_det:,}"
            if health:
                st_total = f"{total_det:,}"

        return (
            hdr_status, hdr_mode, hdr_uptime,
            st_mode, st_port, st_baud, st_last, st_age, st_total,
            p_sec, p_min, p_5min, p_1min, p_total,
        )

    # ── Distribution bars ──────────────────────────────────────────────────────

    dist_outputs = []
    for _c in CANDY:
        dist_outputs += [
            Output(f"dist-bar-{_c}",   "style"),
            Output(f"dist-count-{_c}", "children"),
            Output(f"dist-pct-{_c}",   "children"),
        ]

    @app.callback(*dist_outputs, Input("tick-2s", "n_intervals"))
    def update_distribution(_):
        stats = _api("/stats/summary")
        result = []
        by_color = stats.get("by_color", {}) if stats else {}
        for color, meta in CANDY.items():
            data = by_color.get(color, {"count": 0, "percentage": 0.0})
            pct  = data.get("percentage", 0.0)
            cnt  = data.get("count", 0)
            result += [
                {"width": f"{pct:.1f}%", "background": meta["hex"],
                 "height": "100%", "borderRadius": "3px", "transition": "width .5s ease"},
                str(cnt),
                f"{pct:.1f}%",
            ]
        return result

    # ── Bar chart ──────────────────────────────────────────────────────────────

    @app.callback(Output("chart-bar", "figure"), Input("tick-2s", "n_intervals"))
    def update_bar(_):
        stats = _api("/stats/summary")
        if not stats or not stats.get("by_color"):
            return _empty_fig()

        by_color = stats["by_color"]
        colors_order = [c for c in CANDY if c in by_color]
        counts = [by_color[c]["count"] for c in colors_order]
        hexes  = [CANDY[c]["hex"]    for c in colors_order]
        labels = [c.capitalize()     for c in colors_order]

        fig = go.Figure(go.Bar(
            x=labels, y=counts,
            marker=dict(color=hexes,
                        line=dict(color="rgba(255,255,255,.08)", width=1)),
            text=counts, textposition="outside",
            textfont=dict(size=11, color="#8b949e"),
            hovertemplate="<b>%{x}</b><br>Count: %{y}<extra></extra>",
        ))
        fig.update_layout(
            **_CHART,
            showlegend=False,
            yaxis=dict(gridcolor="#21262d", zeroline=False,
                       linecolor="#30363d", title=""),
            xaxis=dict(gridcolor="rgba(0,0,0,0)", linecolor="#30363d",
                       zeroline=False, title=""),
        )
        return fig

    # ══════════════════════════════════════════════════════════════════════════
    # 5-second tick — pie, timeseries, throughput, confidence, alerts
    # ══════════════════════════════════════════════════════════════════════════

    @app.callback(Output("chart-pie", "figure"), Input("tick-5s", "n_intervals"))
    def update_pie(_):
        stats = _api("/stats/summary")
        if not stats or not stats.get("by_color"):
            return _empty_fig()

        by_color = stats["by_color"]
        colors_order = [c for c in CANDY if c in by_color]
        counts = [by_color[c]["count"] for c in colors_order]
        hexes  = [CANDY[c]["hex"]    for c in colors_order]
        labels = [c.capitalize()     for c in colors_order]

        fig = go.Figure(go.Pie(
            labels=labels, values=counts,
            marker=dict(colors=hexes,
                        line=dict(color="#0d1117", width=2)),
            hole=0.42,
            textinfo="label+percent",
            textfont=dict(size=11),
            hovertemplate="<b>%{label}</b><br>%{value} detections (%{percent})<extra></extra>",
        ))
        fig.update_layout(
            **_CHART,
            margin=dict(l=10, r=10, t=20, b=10),
            legend=dict(orientation="h", x=0.5, xanchor="center",
                        y=-0.12, bgcolor="rgba(0,0,0,0)"),
            annotations=[dict(
                text=f"<b>{stats['total']}</b><br>total",
                x=0.5, y=0.5, font=dict(size=13, color="#f0f6ff"),
                showarrow=False,
            )],
        )
        return fig

    @app.callback(Output("chart-timeseries", "figure"), Input("tick-5s", "n_intervals"))
    def update_timeseries(_):
        data = _api("/stats/timeseries?hours=1")
        if not data:
            return _empty_fig()

        # Bucket into per-color traces
        traces = {}
        for row in data:
            c = row["color"]
            if c not in traces:
                traces[c] = {"x": [], "y": []}
            traces[c]["x"].append(row["timestamp"])
            traces[c]["y"].append(1)

        if not traces:
            return _empty_fig()

        fig = go.Figure()
        for color, pts in traces.items():
            meta = CANDY.get(color, CANDY["unknown"])
            fig.add_trace(go.Scatter(
                x=pts["x"],
                y=[color.capitalize()] * len(pts["x"]),
                mode="markers",
                name=color.capitalize(),
                marker=dict(color=meta["hex"], size=6,
                            symbol="circle", opacity=0.75,
                            line=dict(width=0)),
                hovertemplate=f"<b>{color}</b><br>%{{x}}<extra></extra>",
            ))

        fig.update_layout(
            **_CHART,
            showlegend=True,
            xaxis=dict(gridcolor="#21262d", linecolor="#30363d",
                       zeroline=False, showgrid=True),
            yaxis=dict(gridcolor="#21262d", linecolor="#30363d",
                       zeroline=False, showgrid=False,
                       categoryorder="array",
                       categoryarray=[c.capitalize() for c in CANDY]),
        )
        return fig

    @app.callback(Output("chart-throughput", "figure"), Input("tick-2s", "n_intervals"))
    def update_throughput(_):
        data = _api("/stats/throughput?minutes=15")
        if not data:
            return _empty_fig("No throughput data yet")

        xs = [r["minute"] for r in data]
        ys = [r["count"]  for r in data]

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=xs, y=ys, mode="lines+markers",
            name="candy/min",
            line=dict(color="#39d0d8", width=2.5, shape="spline"),
            marker=dict(size=5, color="#39d0d8"),
            fill="tozeroy",
            fillcolor="rgba(57,208,216,0.08)",
            hovertemplate="<b>%{x}</b><br>%{y} candies<extra></extra>",
        ))
        fig.update_layout(
            **_CHART,
            showlegend=False,
            xaxis=dict(gridcolor="#21262d", linecolor="#30363d", zeroline=False),
            yaxis=dict(gridcolor="#21262d", linecolor="#30363d", zeroline=True,
                       zerolinecolor="#30363d"),
        )
        return fig

    @app.callback(Output("chart-confidence", "figure"), Input("tick-5s", "n_intervals"))
    def update_confidence(_):
        data = _api("/stats/confidence")
        if not data:
            return _empty_fig()

        grouped: dict[str, list[float]] = {}
        for row in data:
            c = row["color"]
            grouped.setdefault(c, []).append(row["confidence"])

        if not grouped:
            return _empty_fig()

        fig = go.Figure()
        for color in CANDY:
            if color not in grouped:
                continue
            meta = CANDY[color]
            vals = grouped[color]
            fig.add_trace(go.Box(
                y=vals,
                name=color.capitalize(),
                marker_color=meta["hex"],
                boxmean="sd",
                line=dict(width=1.5),
                fillcolor=meta["hex"] + "33",
                hovertemplate=f"<b>{color}</b><br>Conf: %{{y:.2f}}<extra></extra>",
            ))

        fig.update_layout(
            **_CHART,
            showlegend=False,
            yaxis=dict(title="Confidence", range=[0, 1.05],
                       gridcolor="#21262d", linecolor="#30363d"),
            xaxis=dict(gridcolor="rgba(0,0,0,0)", linecolor="#30363d"),
        )
        return fig

    # ── Alerts ─────────────────────────────────────────────────────────────────

    @app.callback(Output("alerts-panel", "children"), Input("tick-5s", "n_intervals"))
    def update_alerts(_):
        alerts = _api("/alerts")
        if not alerts:
            return html.Div("No alerts — system nominal.",
                            className="text-muted",
                            style={"fontSize": "12px", "padding": "8px 0"})

        severity_icon = {"critical": "🔴", "warning": "🟡", "info": "🔵"}
        severity_cls  = {"critical": "alert-critical", "warning": "alert-warning", "info": "alert-info"}

        items = []
        for a in alerts:
            sev  = a.get("severity", "info")
            icon = severity_icon.get(sev, "ℹ️")
            cls  = severity_cls.get(sev, "alert-info")
            items.append(
                html.Div(
                    className=f"alert-item {cls}",
                    children=[
                        html.Span(icon, className="alert-icon"),
                        html.Div([
                            html.Div(a.get("title", ""), className="alert-title"),
                            html.Div(a.get("message", ""), className="alert-message"),
                        ]),
                    ],
                )
            )
        return items

    # ── Events table ───────────────────────────────────────────────────────────

    @app.callback(
        Output("events-table-wrapper", "children"),
        Input("tick-2s", "n_intervals"),
    )
    def update_table(_):
        rows = _api("/detections/recent?limit=40")
        if not rows:
            return html.P("Waiting for data…",
                          className="text-muted",
                          style={"fontSize": "12px"})

        def source_chip(src):
            cls = {"simulation": "source-sim",
                   "serial": "source-serial"}.get(src, "source-ext")
            return html.Span(src, className=f"source-badge {cls}")

        def color_chip(color):
            meta = CANDY.get(color, CANDY["unknown"])
            return html.Div(
                className="color-chip",
                children=[
                    html.Span(className="color-dot-sm",
                              style={"background": meta["hex"]}),
                    html.Span(color.capitalize()),
                ],
            )

        table_rows = []
        for r in rows:
            ts = r.get("timestamp", "")[:19].replace("T", " ")
            conf = r.get("confidence", 0)
            payload = r.get("raw_payload") or ""
            if len(payload) > 55:
                payload = payload[:52] + "…"
            table_rows.append(
                html.Tr([
                    html.Td(ts, className="ts"),
                    html.Td(color_chip(r.get("color", "unknown"))),
                    html.Td(f"{conf:.1%}"),
                    html.Td(source_chip(r.get("source", "—"))),
                    html.Td(payload, className="mono text-muted"),
                ])
            )

        return html.Table(
            className="sk-table",
            children=[
                html.Thead(html.Tr([
                    html.Th("Timestamp"),
                    html.Th("Color"),
                    html.Th("Conf."),
                    html.Th("Source"),
                    html.Th("Raw Payload"),
                ])),
                html.Tbody(table_rows),
            ],
        )

    # ══════════════════════════════════════════════════════════════════════════
    # Control panel actions
    # ══════════════════════════════════════════════════════════════════════════

    @app.callback(
        Output("ctrl-msg",    "children"),
        Output("ctrl-msg",    "className"),
        Output("ctrl-msg",    "style"),
        Input("btn-sim-start",      "n_clicks"),
        Input("btn-sim-stop",       "n_clicks"),
        Input("btn-serial-connect", "n_clicks"),
        Input("btn-serial-stop",    "n_clicks"),
        Input("btn-clear",          "n_clicks"),
        State("ctrl-port",     "value"),
        State("ctrl-baud",     "value"),
        State("ctrl-sim-rate", "value"),
        prevent_initial_call=True,
    )
    def handle_controls(
        sim_start, sim_stop, serial_conn, serial_stop, clear,
        port, baud, sim_rate,
    ):
        triggered = ctx.triggered_id

        ok_cls  = "notif notif-ok show"
        err_cls = "notif notif-err show"
        visible = {"display": "block", "marginTop": "10px"}

        if triggered == "btn-sim-start":
            rate = float(sim_rate) if sim_rate else 1.5
            r = _post("/simulation/start", json={"rate": rate})
            if r:
                return f"✓ Simulation started at {rate} candy/s", ok_cls, visible
            return "✗ Could not start simulation.", err_cls, visible

        if triggered == "btn-sim-stop":
            _post("/simulation/stop")
            return "⏹ Simulation stopped.", ok_cls, visible

        if triggered == "btn-serial-connect":
            if not port:
                return "✗ Enter a serial port first.", err_cls, visible
            r = _post("/config/serial", json={"port": port, "baud_rate": int(baud or 9600)})
            if r:
                return f"✓ Connected to {port}.", ok_cls, visible
            return f"✗ Could not connect to {port}.", err_cls, visible

        if triggered == "btn-serial-stop":
            _post("/serial/stop")
            return "⏏ Serial disconnected.", ok_cls, visible

        if triggered == "btn-clear":
            _del("/data/clear")
            return "🗑 Database cleared.", ok_cls, visible

        return no_update, no_update, no_update

    # ── CSV export ─────────────────────────────────────────────────────────────

    @app.callback(
        Output("download-csv", "data"),
        Input("btn-export", "n_clicks"),
        prevent_initial_call=True,
    )
    def export_csv(_):
        try:
            r = requests.get(f"{API}/data/export", timeout=10)
            if r.ok:
                return dcc.send_string(r.text, filename="skittles_detections.csv")
        except Exception as exc:
            logger.error("Export failed: %s", exc)
        return no_update
