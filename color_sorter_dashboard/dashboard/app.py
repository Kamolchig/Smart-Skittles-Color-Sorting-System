"""Dash application factory."""

import dash
import dash_bootstrap_components as dbc

from .callbacks import register_callbacks
from .layout import build_layout


def create_app() -> dash.Dash:
    app = dash.Dash(
        __name__,
        external_stylesheets=[
            dbc.themes.BOOTSTRAP,
            "https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap",
        ],
        title="Smart Skittles Dashboard",
        update_title=None,
        suppress_callback_exceptions=True,
        assets_folder="assets",
    )
    app.layout = build_layout()
    register_callbacks(app)
    return app
