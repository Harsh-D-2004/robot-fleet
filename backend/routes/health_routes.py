"""HTTP route for the health check."""
from fastapi import APIRouter, Depends

from controllers.health_controller import HealthController
from helpers.dependencies import get_health_controller

router = APIRouter()


@router.get("/health")
def health(controller: HealthController = Depends(get_health_controller)):
    return controller.get_health()
