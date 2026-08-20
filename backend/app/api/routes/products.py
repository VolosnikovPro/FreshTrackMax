from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
from app.db.database import get_db
from app.models.product import Product
from app.schemas import ProductCreate, ProductUpdate, ProductOut
from app.core.security import get_current_user, require_roles
from app.models.user import UserRole, User

router = APIRouter()
_admin_or_manager = require_roles(UserRole.admin, UserRole.manager, UserRole.nutrition_manager)


def _get_site_id(user: User) -> int:
    """Get site_id from user, defaulting to 1 if not set (for backward compatibility)."""
    return user.site_id or 1


@router.get("/", response_model=List[ProductOut])
async def list_products(
    active_only: bool = True,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    site_id = _get_site_id(current_user)
    q = select(Product).where(Product.site_id == site_id)
    if active_only:
        q = q.where(Product.is_active == True)
    result = await db.execute(q.order_by(Product.name))
    return result.scalars().all()


@router.get("/{product_id}", response_model=ProductOut)
async def get_product(
    product_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    site_id = _get_site_id(current_user)
    product = await db.get(Product, product_id)
    if not product or product.site_id != site_id:
        raise HTTPException(404, "Product not found")
    return product


@router.post("/", response_model=ProductOut, status_code=201)
async def create_product(
    data: ProductCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(_admin_or_manager),
):
    site_id = data.site_id or _get_site_id(current_user)
    product_data = data.model_dump()
    product_data["site_id"] = site_id
    product = Product(**product_data)
    db.add(product)
    await db.commit()
    await db.refresh(product)
    return product


@router.put("/{product_id}", response_model=ProductOut)
async def update_product(
    product_id: int,
    data: ProductUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(_admin_or_manager),
):
    site_id = _get_site_id(current_user)
    product = await db.get(Product, product_id)
    if not product or product.site_id != site_id:
        raise HTTPException(404, "Product not found")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(product, field, value)
    await db.commit()
    await db.refresh(product)
    return product


@router.delete("/{product_id}", status_code=204)
async def delete_product(
    product_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.admin)),
):
    site_id = _get_site_id(current_user)
    product = await db.get(Product, product_id)
    if not product or product.site_id != site_id:
        raise HTTPException(404, "Product not found")
    product.is_active = False   # soft delete
    await db.commit()