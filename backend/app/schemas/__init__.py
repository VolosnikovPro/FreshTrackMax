from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import date, datetime
from app.models.user import UserRole


# ─── Auth ────────────────────────────────────────────────────────────────────

class MaxAuthRequest(BaseModel):
    initData: str


class LocalLoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: "UserOut"


# ─── Site ─────────────────────────────────────────────────────────────────────

class SiteCreate(BaseModel):
    name: str
    code: str
    description: Optional[str] = None


class SiteUpdate(BaseModel):
    name: Optional[str] = None
    code: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None


class SiteOut(BaseModel):
    id: int
    name: str
    code: str
    description: Optional[str]
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


# ─── User ─────────────────────────────────────────────────────────────────────

class UserOut(BaseModel):
    id: int
    site_id: int
    username: str
    display_name: str
    role: UserRole
    is_active: bool
    max_user_id: int | None

    model_config = {"from_attributes": True}


class UserCreate(BaseModel):
    username: str
    display_name: str = ""
    role: UserRole = UserRole.storekeeper
    password: Optional[str] = None
    max_user_id: Optional[int] = None
    site_id: Optional[int] = None


class UserUpdate(BaseModel):
    username: Optional[str] = None
    display_name: Optional[str] = None
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None
    password: Optional[str] = None
    max_user_id: Optional[int] = None


# ─── Product ──────────────────────────────────────────────────────────────────

class ProductCreate(BaseModel):
    site_id: Optional[int] = None
    name: str
    sku: Optional[str] = None
    unit: str = "kg"
    category: Optional[str] = None
    description: Optional[str] = None


class ProductUpdate(BaseModel):
    name: Optional[str] = None
    sku: Optional[str] = None
    unit: Optional[str] = None
    category: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None


class ProductOut(BaseModel):
    id: int
    site_id: int
    name: str
    sku: Optional[str]
    unit: str
    category: Optional[str]
    description: Optional[str]
    is_active: bool

    model_config = {"from_attributes": True}


# ─── Batch ────────────────────────────────────────────────────────────────────

class BatchCreate(BaseModel):
    site_id: Optional[int] = None
    product_id: int
    batch_number: Optional[str] = None
    quantity: float = Field(..., gt=0)
    unit: str = "kg"
    expiry_date: date
    received_date: Optional[date] = None
    notes: Optional[str] = None


class BatchUpdate(BaseModel):
    batch_number: Optional[str] = None
    quantity: Optional[float] = None
    expiry_date: Optional[date] = None
    received_date: Optional[date] = None
    notes: Optional[str] = None


class BatchOut(BaseModel):
    id: int
    site_id: int
    product_id: int
    product_name: str = ""
    batch_number: Optional[str]
    quantity: float
    unit: str
    expiry_date: date
    received_date: Optional[date]
    days_until_expiry: int
    notes: Optional[str]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ─── Cost ─────────────────────────────────────────────────────────────────────

class CostCreate(BaseModel):
    site_id: Optional[int] = None
    product_id: int
    cost_per_unit: float = Field(..., gt=0)
    currency: str = "RUB"
    effective_date: date
    notes: Optional[str] = None


class CostUpdate(BaseModel):
    cost_per_unit: Optional[float] = None
    effective_date: Optional[date] = None
    notes: Optional[str] = None


class CostOut(BaseModel):
    id: int
    site_id: int
    product_id: int
    product_name: str = ""
    cost_per_unit: float
    currency: str
    effective_date: date
    notes: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


# ─── Consumption ──────────────────────────────────────────────────────────────

class ConsumptionCreate(BaseModel):
    site_id: Optional[int] = None
    product_id: int
    date: date
    quantity_used: float = Field(..., gt=0)
    unit: str = "kg"
    notes: Optional[str] = None


class ConsumptionUpdate(BaseModel):
    quantity_used: Optional[float] = None
    notes: Optional[str] = None


class ConsumptionOut(BaseModel):
    id: int
    site_id: int
    product_id: int
    product_name: str = ""
    date: date
    quantity_used: float
    unit: str
    notes: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


# ─── Headcount ────────────────────────────────────────────────────────────────

class HeadcountCreate(BaseModel):
    site_id: Optional[int] = None
    date: date
    count: int = Field(..., gt=0)
    notes: Optional[str] = None


class HeadcountUpdate(BaseModel):
    count: Optional[int] = None
    notes: Optional[str] = None


class HeadcountOut(BaseModel):
    id: int
    site_id: int
    date: date
    count: int
    notes: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


# ─── Admin Dashboard ──────────────────────────────────────────────────────────

class AdminSummary(BaseModel):
    total_products: int
    total_batches: int
    expiring_soon_urgent: int       # < 16 days
    expiring_soon_planned: int      # < 46 days
    total_products_with_cost: int
    today_headcount: Optional[int]
    today_consumption_entries: int


# ─── Notification ─────────────────────────────────────────────────────────────

class NotificationConfig(BaseModel):
    notification_time: str = "09:00"
    base_day: str = "sunday"
    max_per_week: int = 6


class NotificationTriggerResponse(BaseModel):
    sent: int
    recipients: List[str]
    products_included: int


# ─── Google Sheets ────────────────────────────────────────────────────────────

class SheetsImportRequest(BaseModel):
    spreadsheet_id: Optional[str] = None
    sheet_name: str = "Products"
    import_type: str = "products"   # products | batches | costs


class SheetsImportResult(BaseModel):
    imported: int
    skipped: int
    errors: List[str]


TokenResponse.model_rebuild()
