from fastapi import APIRouter

from app.api.routes.compare import router as compare_router
from app.api.routes.dashboard import router as dashboard_router
from app.api.routes.health import router as health_router
from app.api.routes.metrics import router as metrics_router
from app.api.routes.news import router as news_router
from app.api.routes.power import router as power_router
from app.api.routes.regions import router as regions_router
from app.api.routes.rt_schedule import router as rt_schedule_router
from app.api.routes.weather import router as weather_router
from app.api.routes.reasoning import router as reasoning_router

api_router = APIRouter()
api_router.include_router(health_router, tags=["health"])
api_router.include_router(regions_router, tags=["regions"])
api_router.include_router(dashboard_router, tags=["dashboard"])
api_router.include_router(rt_schedule_router, tags=["rt-schedule"])
api_router.include_router(metrics_router, tags=["metrics"])
api_router.include_router(power_router, tags=["power"])
api_router.include_router(compare_router, tags=["compare"])
api_router.include_router(weather_router, tags=["weather"])
api_router.include_router(news_router, tags=["news"])
api_router.include_router(reasoning_router, tags=["reasoning"])
