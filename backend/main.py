from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from uvicorn.config import LOGGING_CONFIG
from app.api.routes import (
    auth, products, batches, costs, consumption,
    headcount, notifications, admin, sheets, sites
)
from app.core.config import settings
from app.db.database import create_tables
import uvicorn

app = FastAPI(
    title="FreshTrack MVP API",
    description="Expiry date control and raw material consumption tracking system",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def on_startup():
    await create_tables()


app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(products.router, prefix="/api/products", tags=["products"])
app.include_router(batches.router, prefix="/api/batches", tags=["batches"])
app.include_router(costs.router, prefix="/api/costs", tags=["costs"])
app.include_router(consumption.router, prefix="/api/consumption", tags=["consumption"])
app.include_router(headcount.router, prefix="/api/headcount", tags=["headcount"])
app.include_router(notifications.router, prefix="/api/notifications", tags=["notifications"])
app.include_router(admin.router, prefix="/api/admin", tags=["admin"])
app.include_router(sheets.router, prefix="/api/sheets", tags=["sheets"])
app.include_router(sites.router, prefix="/api/sites", tags=["sites"])


@app.get("/health")
async def health_check():
    return {"status": "ok", "version": "0.1.0"}

if __name__ == "__main__":
    LOGGING_CONFIG["formatters"]["default"]["fmt"] = "%(asctime)s [%(name)s] %(levelprefix)s %(message)s"
    uvicorn.run(app, host="0.0.0.0", port=80)
