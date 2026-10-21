"""
Configuration and Agronomic Prototype Assumptions.

IMPORTANT SCIENTIFIC INTEGRITY NOTICE:
The thresholds and penalties defined herein represent empirical, configurable
PROTOTYPE ASSUMPTIONS derived from general post-harvest handling literature.
They are NOT calibrated agricultural spoilage probabilities or validated shelf-life
prediction models. All MQ-135 values are treated strictly as an uncalibrated relative
resistance ratio (Rs/R0), never as exact ethylene or VOC concentrations.
"""

from pathlib import Path
from pydantic_settings import BaseSettings

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
UPLOAD_DIR = BASE_DIR / "uploads"

# Ensure runtime directories exist
DATA_DIR.mkdir(parents=True, exist_ok=True)
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

class Settings(BaseSettings):
    PROJECT_NAME: str = "Post-Harvest Spoilage Prediction & Sell-First Advisor"
    VERSION: str = "0.1.0-phase1-prototype"
    DATABASE_URL: str = f"sqlite:///{DATA_DIR / 'banana_advisor.db'}"

    # Default Configurable Prototype Weights (Sum to 1.0)
    DEFAULT_WEIGHT_VISION: float = 0.40
    DEFAULT_WEIGHT_TEMP: float = 0.25
    DEFAULT_WEIGHT_HUMIDITY: float = 0.20
    DEFAULT_WEIGHT_GAS: float = 0.15
    DEFAULT_WEIGHT_WEIGHT_LOSS: float = 0.00  # Load cell optional

    # Stale Telemetry Threshold (Seconds) - 30 minutes
    STALE_THRESHOLD_SECONDS: int = 1800

    # Prototype Ripeness Stage Penalties (0 - 100)
    # Note: Only real detected stages carry penalties. Unavailable vision is excluded.
    PENALTY_RIPENESS_UNDER_RIPE: float = 10.0
    PENALTY_RIPENESS_HALF_RIPE: float = 20.0
    PENALTY_RIPENESS_RIPE: float = 35.0
    PENALTY_RIPENESS_OVER_RIPE: float = 75.0
    PENALTY_RIPENESS_DECAYING: float = 95.0

    # Temperature Prototype Thresholds (°C)
    TEMP_OPTIMAL_MIN: float = 13.0
    TEMP_OPTIMAL_MAX: float = 15.0
    TEMP_CHILLING_THRESHOLD: float = 12.0
    TEMP_ELEVATED_MAX: float = 20.0

    # Humidity Prototype Thresholds (% RH)
    HUMIDITY_OPTIMAL_MIN: float = 85.0
    HUMIDITY_OPTIMAL_MAX: float = 90.0

    # MQ-135 Clean-Air Baseline Resistance (Rs / R0 ratio reference)
    GAS_RATIO_NOMINAL_MIN: float = 0.95

settings = Settings()
