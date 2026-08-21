import hmac
import hashlib
import json
from urllib.parse import parse_qsl
from operator import itemgetter
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.database import get_db
from app.models.user import User, UserRole
from app.models.site import Site
from app.schemas import LocalLoginRequest, TokenResponse, UserOut, MaxAuthRequest
from app.core.security import verify_password, create_access_token, hash_password
from app.core.config import settings

router = APIRouter()


@router.post("/login", response_model=TokenResponse)
async def local_login(data: LocalLoginRequest, db: AsyncSession = Depends(get_db)):
    """Local username/password login (for dev / admin use)."""
    result = await db.execute(select(User).where(User.username == data.username))
    user = result.scalar_one_or_none()

    if not user or not user.hashed_password:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not verify_password(data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account disabled")

    token = create_access_token({"sub": str(user.id)})
    return TokenResponse(access_token=token, user=UserOut.model_validate(user))


@router.post("/max", response_model=TokenResponse)
async def max_auth(data: MaxAuthRequest, db: AsyncSession = Depends(get_db)):
    """
    AUTH via MAX messenger.
    """
    max_user_id = get_max_user_id(data.initData)

    user = None
    if max_user_id is not None:
        result = await db.execute(select(User).where(User.max_user_id == max_user_id))
        user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=404,
            detail="MAX account not linked. Ask admin to create your account."
        )
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account disabled")

    token = create_access_token({"sub": str(user.id)})
    return TokenResponse(access_token=token, user=UserOut.model_validate(user))


@router.post("/seed-admin")
async def seed_admin(db: AsyncSession = Depends(get_db)):
    """
    One-time admin seeding endpoint. Disable in production.
    Creates a default site and admin user with password 'admin123' if not exists.
    """
    result = await db.execute(select(User).where(User.username == "admin"))
    existing = result.scalar_one_or_none()
    if existing:
        return {"detail": "Admin already exists"}

    # Ensure a default site exists for the admin
    site_result = await db.execute(select(Site).where(Site.code == "DEFAULT"))
    site = site_result.scalar_one_or_none()
    if site is None:
        site = Site(name="Основной объект", code="DEFAULT", is_active=True)
        db.add(site)
        await db.flush()

    admin = User(
        username="admin",
        display_name="Administrator",
        role=UserRole.admin,
        max_user_id="local-admin",
        site_id=site.id,
        hashed_password=hash_password("admin123"),
    )
    db.add(admin)
    await db.commit()
    return {"detail": "Admin created", "username": "admin", "password": "admin123"}


def get_max_user_id(initData: str) -> int:
    # Парсим строку данных (key1=value1&key2=value2...) в список кортежей
    # parse_qsl автоматически выполняет URL-декодирование значений
    params = list(dict(parse_qsl(initData, keep_blank_values=True)).items())

    # Ищем параметр hash и удаляем его из списка параметров для проверки
    original_hash = next((value for key, value in params if key == 'hash'), None)

    # Если хеш отсутствует — валидация невозможна
    if not original_hash:
        return False

    # Формируем список параметров без hash, сортируем по ключу (a -> z)
    params_to_sign = sorted([(k, v) for k, v in params if k != 'hash'], key=itemgetter(0))

    # Формируем строку для подписи с разделителем \n, исключаем hash
    launch_params = '\n'.join(f'{k}={v}' for k, v in params_to_sign)

    # Создаём secret_key: подписываем токен бота с помощью HMAC-SHA256,
    # используя строку "WebAppData" в качестве ключа
    secret_key = hmac.new(
        key=b"WebAppData",
        msg=settings.MAX_BOT_TOKEN.encode('utf-8'),
        digestmod=hashlib.sha256
    ).digest()

    # Вычисляем подпись WebAppData с помощью HMAC-SHA256, используя secret_key
    hash = hmac.new(
        key=secret_key,
        msg=launch_params.encode('utf-8'),
        digestmod=hashlib.sha256
    ).hexdigest()

    # Сравниваем полученный хеш с пришедшим
    if hmac.compare_digest(hash, original_hash):
        max_id = json.loads(dict(parse_qsl(initData))["user"])["id"]
        return max_id
    return None