import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).parent.parent


class Settings:
    SERIAL_PORT: str = os.getenv("SERIAL_PORT", "COM3")
    BAUD_RATE: int = int(os.getenv("BAUD_RATE", "9600"))
    DB_PATH: str = str(BASE_DIR / "data" / "skittles.db")
    API_HOST: str = os.getenv("API_HOST", "0.0.0.0")
    API_PORT: int = int(os.getenv("API_PORT", "8000"))
    DASHBOARD_HOST: str = os.getenv("DASHBOARD_HOST", "0.0.0.0")
    DASHBOARD_PORT: int = int(os.getenv("DASHBOARD_PORT", "8050"))
    SIMULATION_MODE: bool = os.getenv("SIMULATION_MODE", "true").lower() == "true"
    SIMULATION_RATE: float = float(os.getenv("SIMULATION_RATE", "1.5"))


settings = Settings()
