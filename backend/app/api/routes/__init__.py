from fastapi import APIRouter
from app.api.routes import (
    admin,
    sites,
    auth,
    products,
    batches,
    consumption,
    costs,
    headcount,
    notifications,
    sheets,
)

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(admin.router, prefix="/admin", tags=["admin"])
api_router.include_router(sites.router, prefix="/sites", tags=["sites"])
api_router.include_router(products.router, prefix="/products", tags=["products"])
api_router.include_router(batches.router, prefix="/batches", tags=["batches"])
api_router.include_router(consumption.router, prefix="/consumption", tags=["consumption"])
api_router.include_router(costs.router, prefix="/costs", tags=["costs"])
api_router.include_router(headcount.router, prefix="/headcount", tags=["headcount"])
api_router.include_router(notifications.router, prefix="/notifications", tags=["notifications"])
api_router.include_router(sheets.router, prefix="/sheets", tags=["sheets"])