import os, json
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()
BASE_DIR = Path(__file__).resolve().parent.parent
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./banking_poc.db")
API_PREFIX = "/api/v1"
AI_CONFIDENCE_THRESHOLD = float(os.getenv("AI_CONFIDENCE_THRESHOLD", "0.75"))
SLA_MONITOR_INTERVAL_SECONDS = int(os.getenv("SLA_MONITOR_INTERVAL_SECONDS", "60"))
CONFIG = json.loads((BASE_DIR / "data" / "config.json").read_text(encoding="utf-8"))
