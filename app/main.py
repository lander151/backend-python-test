from fastapi import FastAPI

from routers.requests import requests_router
from settings import settings

app = FastAPI(
    title=settings.app_name, version=settings.app_version, debug=settings.debug
)

app.include_router(requests_router, prefix="/v1")
