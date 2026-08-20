from app.models.user import User, UserRole
from app.models.site import Site
from app.models.product import Product
from app.models.batch import Batch
from app.models.consumption import RawMaterialCost, DailyConsumption, DailyHeadcount

# Aliases
cost = RawMaterialCost
headcount = DailyHeadcount

__all__ = [
    "User", "UserRole",
    "Site",
    "Product",
    "Batch",
    "RawMaterialCost", "DailyConsumption", "DailyHeadcount",
]