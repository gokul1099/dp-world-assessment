from fastapi import APIRouter

from app.schemas.health import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> HealthResponse:
    """Liveness check used by Cloud Run, deploy scripts and the frontend."""
    return HealthResponse(status="ok")
