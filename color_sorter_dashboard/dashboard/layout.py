"""Dashboard layout — Dark Industrial IoT theme."""

import dash_bootstrap_components as dbc
from dash import dcc, html

# ── Colour metadata ────────────────────────────────────────────────────────────
CANDY = {
    "red":     {"hex": "#FF3B3B", "glow": "rgba(255,59,59,0.35)",   "icon": "🔴"},
    "orange":  {"hex": "#FF8C00", "glow": "rgba(255,140,0,0.35)",   "icon": "🟠"},
    "yellow":  {"hex": "#FFE033", "glow": "rgba(255,224,51,0.35)",  "icon": "🟡"},
    "green":   {"hex": "#3BFF6E", "glow": "rgba(59,255,110,0.35)",  "icon": "🟢"},
    "blue":    {"hex": "#3B8FFF", "glow": "rgba(59,143,255,0.35)",  "icon": "🔵"},
    "purple":  {"hex": "#C77DFF", "glow": "rgba(199,125,255,0.35)", "icon": "🟣"},
    "unknown": {"hex": "#6E7681", "glow": "rgba(110,118,129,0.20)", "icon": "⚫"},
}

BAUD_OPTIONS = [
    {"label": "9 600",   "value": 9600},
    {"label": "19 200",  "value": 19200},
    {"label": "38 400",  "value": 38400},
    {"label": "57 600",  "value": 57600},
    {"label": "115 200", "value": 115200},
]


# ── Reusable helpers ───────────────────────────────────────────────────────────

def _card(title: str, children, extra_class: str = "", style: dict | None = None):
    return html.Div(
        className=f"sk-card {extra_class}",
        style=style,
        children=[
            html.P(title, className="sk-card-title"),
            *([children] if not isinstance(children, list) else children),
        ],
    )


def _stat_row(key: str, value_id: str, default: str = "—"):
    return html.Div(
        className="stat-row",
        children=[
            html.Span(key, className="stat-key"),
            html.Span(default, id=value_id, className="stat-val"),
        ],
    )


# ── Header ─────────────────────────────────────────────────────────────────────

def _header():
    return html.Div(
        className="sk-header",
        children=[
            dbc.Row(
                align="center",
                children=[
                    dbc.Col(
                        children=[
                            html.H1(
                                children=[
                                    html.Span("🍬", style={"marginRight": "8px"}),
                                    "Smart Skittles Color Sorting Dashboard",
                                ],
                                className="sk-header-title",
                            ),
                            html.P(
                                "Real-time monitoring system for candy classification",
                                className="sk-header-sub",
                            ),
                        ],
                        xs=12, md=7,
                    ),
                    dbc.Col(
                        className="d-flex align-items-center justify-content-md-end gap-2 mt-2 mt-md-0",
                        children=[
                            html.Span(id="hdr-status-badge",  children=[]),
                            html.Span(id="hdr-mode-badge",    children=[]),
                            html.Span(id="hdr-uptime",
                                      className="text-muted",
                                      style={"fontSize": "11px"}),
                        ],
                        xs=12, md=5,
                    ),
                ],
            ),
        ],
    )


# ── Row 1 — Status / Hero / Performance ───────────────────────────────────────

def _system_status_card():
    return _card(
        "System Status",
        [
            _stat_row("Mode",        "st-mode"),
            _stat_row("Serial Port", "st-port"),
            _stat_row("Baud Rate",   "st-baud"),
            _stat_row("Last Detection", "st-last"),
            _stat_row("Age",         "st-age"),
            _stat_row("DB Records",  "st-total"),
        ],
    )


def _hero_card():
    return html.Div(
        id="hero-card",
        className="sk-hero-card",
        style={"--hero-glow": "transparent"},
        children=[
            html.Div(
                id="hero-orb",
                className="candy-orb",
                style={"background": "#21262d", "boxShadow": "none"},
                children="?",
            ),
            html.H2("—", id="hero-name", className="candy-name"),
            html.P("TCS34725 · Sensor", className="candy-sensor"),
            html.Div(
                [
                    html.Div(
                        className="flex-between",
                        children=[
                            html.Span("Confidence", className="conf-label"),
                            html.Span("—", id="hero-conf-text",
                                      style={"fontWeight": 700, "color": "#f0f6ff"}),
                        ],
                    ),
                    html.Div(
                        className="conf-track",
                        children=html.Div(
                            id="hero-conf-bar",
                            className="conf-fill",
                            style={"width": "0%"},
                        ),
                    ),
                ],
                style={"width": "100%"},
            ),
            html.P("—", id="hero-timestamp",
                   style={"fontSize": "11px", "color": "#6e7681", "marginTop": "8px",
                          "fontFamily": "Consolas, monospace"}),
        ],
    )


def _performance_card():
    return html.Div(
        className="sk-card",
        children=[
            html.P("Throughput", className="sk-card-title"),
            dbc.Row(
                className="mb-3",
                children=[
                    dbc.Col([
                        html.Div("—", id="perf-per-sec",  className="big-metric"),
                        html.Div("candy / sec",            className="big-metric-label"),
                    ], xs=6),
                    dbc.Col([
                        html.Div("—", id="perf-per-min",  className="big-metric"),
                        html.Div("candy / min",            className="big-metric-label"),
                    ], xs=6),
                ],
            ),
            html.Hr(style={"borderColor": "#30363d", "margin": "10px 0"}),
            _stat_row("Last 5 min",     "perf-5min"),
            _stat_row("Last 1 min",     "perf-1min"),
            _stat_row("Total processed", "perf-total"),
        ],
    )


# ── Row 2 — Distribution + Bar chart ──────────────────────────────────────────

def _distribution_card():
    rows = []
    for color, meta in CANDY.items():
        rows.append(
            html.Div(
                className="dist-row",
                children=[
                    html.Div(
                        className="dist-dot-label",
                        children=[
                            html.Span(className="dist-dot",
                                      style={"background": meta["hex"]}),
                            html.Span(color.capitalize()),
                        ],
                    ),
                    html.Div(
                        className="dist-track",
                        children=html.Div(
                            id=f"dist-bar-{color}",
                            className="dist-fill",
                            style={"width": "0%", "background": meta["hex"]},
                        ),
                    ),
                    html.Span("0", id=f"dist-count-{color}", className="dist-count"),
                    html.Span("0%", id=f"dist-pct-{color}",  className="dist-pct"),
                ],
            )
        )
    return _card("Color Distribution", rows)


def _bar_chart_card():
    return _card(
        "Detections per Color",
        dcc.Graph(
            id="chart-bar",
            config={"displayModeBar": False},
            style={"height": "300px"},
        ),
    )


# ── Row 3 — Pie + Time series ─────────────────────────────────────────────────

def _pie_chart_card():
    return _card(
        "Color Proportion",
        dcc.Graph(
            id="chart-pie",
            config={"displayModeBar": False},
            style={"height": "310px"},
        ),
    )


def _timeseries_card():
    return _card(
        "Detections Timeline (last hour)",
        dcc.Graph(
            id="chart-timeseries",
            config={"displayModeBar": False},
            style={"height": "310px"},
        ),
    )


# ── Row 4 — Throughput trend ───────────────────────────────────────────────────

def _throughput_card():
    return _card(
        "Real-time Throughput (candy / min)",
        dcc.Graph(
            id="chart-throughput",
            config={"displayModeBar": False},
            style={"height": "220px"},
        ),
    )


# ── Row 5 — Confidence + Alerts ───────────────────────────────────────────────

def _confidence_card():
    return _card(
        "Confidence by Color",
        dcc.Graph(
            id="chart-confidence",
            config={"displayModeBar": False},
            style={"height": "270px"},
        ),
    )


def _alerts_card():
    return _card(
        "Smart Alerts",
        html.Div(id="alerts-panel", children=[
            html.Div(
                "No alerts — system nominal.",
                className="text-muted",
                style={"fontSize": "12px", "padding": "8px 0"},
            )
        ]),
    )


# ── Row 6 — Recent detections table ───────────────────────────────────────────

def _events_card():
    return _card(
        "Recent Detections",
        html.Div(
            id="events-table-wrapper",
            className="overflow-auto",
            style={"maxHeight": "320px"},
            children=html.P("Waiting for data…",
                            className="text-muted",
                            style={"fontSize": "12px"}),
        ),
    )


# ── Row 7 — Control panel ─────────────────────────────────────────────────────

def _control_panel():
    return _card(
        "Control Panel",
        [
            dbc.Row(
                align="end",
                className="g-3",
                children=[
                    # Port
                    dbc.Col(
                        [
                            html.Label("Serial Port", className="text-muted mb-1",
                                       style={"fontSize": "11px", "display": "block"}),
                            dcc.Input(
                                id="ctrl-port",
                                type="text",
                                value="COM3",
                                placeholder="COM3 or /dev/ttyUSB0",
                                className="sk-ctrl-input",
                            ),
                        ],
                        xs=12, sm=6, md=3,
                    ),
                    # Baud
                    dbc.Col(
                        [
                            html.Label("Baud Rate", className="text-muted mb-1",
                                       style={"fontSize": "11px", "display": "block"}),
                            dcc.Dropdown(
                                id="ctrl-baud",
                                options=BAUD_OPTIONS,
                                value=9600,
                                clearable=False,
                                style={"fontSize": "13px"},
                            ),
                        ],
                        xs=12, sm=6, md=2,
                    ),
                    # Sim rate
                    dbc.Col(
                        [
                            html.Label("Sim Rate (candy/s)", className="text-muted mb-1",
                                       style={"fontSize": "11px", "display": "block"}),
                            dcc.Input(
                                id="ctrl-sim-rate",
                                type="number",
                                value=1.5,
                                min=0.1, max=20, step=0.5,
                                className="sk-ctrl-input",
                            ),
                        ],
                        xs=12, sm=6, md=2,
                    ),
                    # Buttons
                    dbc.Col(
                        [
                            html.Div(
                                className="d-flex flex-wrap gap-2",
                                children=[
                                    html.Button("⏵ Start Simulation",
                                                id="btn-sim-start",
                                                className="sk-btn sk-btn-success",
                                                n_clicks=0),
                                    html.Button("⏹ Stop Simulation",
                                                id="btn-sim-stop",
                                                className="sk-btn sk-btn-warn",
                                                n_clicks=0),
                                    html.Button("🔌 Connect Serial",
                                                id="btn-serial-connect",
                                                className="sk-btn",
                                                n_clicks=0),
                                    html.Button("⏏ Disconnect",
                                                id="btn-serial-stop",
                                                className="sk-btn",
                                                n_clicks=0),
                                    html.Button("🗑 Clear DB",
                                                id="btn-clear",
                                                className="sk-btn sk-btn-danger",
                                                n_clicks=0),
                                    html.Button("📥 Export CSV",
                                                id="btn-export",
                                                className="sk-btn",
                                                n_clicks=0),
                                ],
                            ),
                        ],
                        xs=12, md=5,
                    ),
                ],
            ),
            html.Div(id="ctrl-msg", className="notif", style={"display": "none"}),
            dcc.Download(id="download-csv"),
        ],
    )


# ── Full layout ────────────────────────────────────────────────────────────────

def build_layout():
    return html.Div(
        style={"background": "#080c14", "minHeight": "100vh", "paddingBottom": "40px"},
        children=[
            # Timers
            dcc.Interval(id="tick-1s",  interval=1_000,  n_intervals=0),
            dcc.Interval(id="tick-2s",  interval=2_000,  n_intervals=0),
            dcc.Interval(id="tick-5s",  interval=5_000,  n_intervals=0),
            dcc.Interval(id="tick-15s", interval=15_000, n_intervals=0),

            # Header
            _header(),

            # Main content
            dbc.Container(fluid=True, style={"padding": "16px 24px"}, children=[

                # ── Row 1: Status / Hero / Performance ────────────────
                html.Div(className="section-title", children="Live Monitoring"),
                dbc.Row(className="g-3 mb-3", children=[
                    dbc.Col(_system_status_card(), xs=12, md=3),
                    dbc.Col(_hero_card(),          xs=12, md=6),
                    dbc.Col(_performance_card(),   xs=12, md=3),
                ]),

                # ── Row 2: Distribution + Bar ─────────────────────────
                html.Div(className="section-title", children="Distribution Analysis"),
                dbc.Row(className="g-3 mb-3", children=[
                    dbc.Col(_distribution_card(), xs=12, md=4),
                    dbc.Col(_bar_chart_card(),    xs=12, md=8),
                ]),

                # ── Row 3: Pie + Timeline ─────────────────────────────
                dbc.Row(className="g-3 mb-3", children=[
                    dbc.Col(_pie_chart_card(),    xs=12, md=5),
                    dbc.Col(_timeseries_card(),   xs=12, md=7),
                ]),

                # ── Row 4: Throughput ─────────────────────────────────
                html.Div(className="section-title", children="Performance Trend"),
                dbc.Row(className="g-3 mb-3", children=[
                    dbc.Col(_throughput_card(), xs=12),
                ]),

                # ── Row 5: Confidence + Alerts ─────────────────────────
                html.Div(className="section-title", children="Diagnostics & Alerts"),
                dbc.Row(className="g-3 mb-3", children=[
                    dbc.Col(_confidence_card(), xs=12, md=5),
                    dbc.Col(_alerts_card(),     xs=12, md=7),
                ]),

                # ── Row 6: Recent detections ───────────────────────────
                html.Div(className="section-title", children="Event Log"),
                dbc.Row(className="g-3 mb-3", children=[
                    dbc.Col(_events_card(), xs=12),
                ]),

                # ── Row 7: Controls ────────────────────────────────────
                html.Div(className="section-title", children="Control Panel"),
                dbc.Row(className="g-3", children=[
                    dbc.Col(_control_panel(), xs=12),
                ]),
            ]),
        ],
    )
