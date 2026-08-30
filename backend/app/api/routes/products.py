from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
from app.db.database import get_db
from app.models.product import Product
from app.schemas import ProductCreate, ProductUpdate, ProductOut
from app.core.security import get_current_user, require_roles
from app.models.user import UserRole, User
from app.core.site_access import resolve_site_id

router = APIRouter()
_product_creator = require_roles(UserRole.superadmin, UserRole.admin, UserRole.storekeeper)
_product_reader = require_roles(UserRole.superadmin, UserRole.admin, UserRole.storekeeper, UserRole.nutrition_manager)


@router.get("/", response_model=List[ProductOut])
async def list_products(
    active_only: bool = True,
    site_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(_product_reader),
):
    site_id = await resolve_site_id(db, current_user, site_id)
    q = select(Product).where(Product.site_id == site_id)
    if active_only:
        q = q.where(Product.is_active == True)
    result = await db.execute(q.order_by(Product.name))
    return result.scalars().all()


@router.get("/{product_id}", response_model=ProductOut)
async def get_product(
    product_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(_product_reader),
):
    site_id = await resolve_site_id(db, current_user)
    product = await db.get(Product, product_id)
    if not product or product.site_id != site_id:
        raise HTTPException(404, "Product not found")
    return product


@router.post("/", response_model=ProductOut, status_code=201)
async def create_product(
    data: ProductCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(_product_creator),
):
    site_id = await resolve_site_id(db, current_user, data.site_id)
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
    current_user: User = Depends(_product_creator),
):
    # Product records are source documents. Corrections must be represented by
    # a new record/import, never by changing historical master data in place.
    raise HTTPException(409, detail={"code": "PRODUCT_IMMUTABLE", "message": "Существующий продукт нельзя редактировать"})


@router.delete("/{product_id}", status_code=204)
async def delete_product(
    product_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.superadmin, UserRole.admin)),
):
    raise HTTPException(409, detail={"code": "PRODUCT_IMMUTABLE", "message": "Существующий продукт нельзя удалять"})
