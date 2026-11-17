from app.api.batches import router as batches_router
from app.api.telemetry_simulated import router as telemetry_sim_router
from app.api.telemetry_hardware import router as telemetry_hw_router
from app.api.telemetry_data import router as telemetry_data_router
from app.api.vision import router as vision_router
from app.api.advisor import router as advisor_router

__all__ = [
    "batches_router",
    "telemetry_sim_router",
    "telemetry_hw_router",
    "telemetry_data_router",
    "vision_router",
    "advisor_router",
]
