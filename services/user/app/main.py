from contextlib import asynccontextmanager
from datetime import datetime, timezone
import logging
import os
import uuid
from fastapi import Depends, FastAPI, Header, HTTPException, Request, Response, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
import jwt
from pymongo.errors import DuplicateKeyError
from .config import settings
from .database import close_db, connect_db, get_db
from .models import (
    AdminCreateUserRequest,
    AuthResponse,
    LoginRequest,
    RegisterRequest,
    UserResponse,
    UserRole,
)
from .security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] corr_id=%(correlation_id)s %(message)s",
)
logger = logging.getLogger(settings.SERVICE_NAME)
bearer_scheme = HTTPBearer(auto_error=False)


class CorrelationFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        if not hasattr(record, "correlation_id"):
            record.correlation_id = "-"
        return True


logger.addFilter(CorrelationFilter())
for handler in logging.getLogger().handlers:
    handler.addFilter(CorrelationFilter())


async def _seed_privileged_users() -> None:
    """Optional dev/local seeding for ADMIN and CINEMA accounts via env vars."""
    db = get_db()
    now = datetime.now(timezone.utc)

    seeds: list[tuple[str, str, str, UserRole, list[str]]] = []

    admin_email = os.getenv("SEED_ADMIN_EMAIL", "").strip().lower()
    admin_password = os.getenv("SEED_ADMIN_PASSWORD", "")
    if admin_email and admin_password:
        seeds.append(("Platform Admin", admin_email, admin_password, "ADMIN", []))

    cinema_email = os.getenv("SEED_CINEMA_EMAIL", "").strip().lower()
    cinema_password = os.getenv("SEED_CINEMA_PASSWORD", "")
    raw_cinema_ids = os.getenv("SEED_CINEMA_IDS", "")
    cinema_ids = [c.strip() for c in raw_cinema_ids.split(",") if c.strip()]
    if cinema_email and cinema_password:
        seeds.append(("Cinema Partner", cinema_email, cinema_password, "CINEMA", cinema_ids))

    for name, email, password, role, c_ids in seeds:
        existing = await db.users.find_one({"email": email})
        if existing:
            continue
        user_id = f"usr_{uuid.uuid4().hex[:8]}"
        await db.users.insert_one(
            {
                "user_id": user_id,
                "name": name,
                "email": email,
                "password_hash": hash_password(password),
                "role": role,
                "cinema_ids": c_ids,
                "created_at": now,
            }
        )
        logger.info(
            f"Seeded {role} user {user_id} ({email})",
            extra={"correlation_id": "startup-seed"},
        )


@asynccontextmanager
async def lifespan(_: FastAPI):
    await connect_db()
    await _seed_privileged_users()
    yield
    await close_db()


app = FastAPI(title="BMS User Service", version="1.0.0", lifespan=lifespan)


@app.middleware("http")
async def correlation_middleware(request: Request, call_next):
    corr_id = request.headers.get("X-Correlation-ID") or str(uuid.uuid4())
    request.state.correlation_id = corr_id
    response: Response = await call_next(request)
    response.headers["X-Correlation-ID"] = corr_id
    return response


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> dict:
    corr_id = getattr(request.state, "correlation_id", "-")
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid Bearer token",
            headers={"X-Correlation-ID": corr_id},
        )
    try:
        claims = decode_access_token(credentials.credentials)
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"X-Correlation-ID": corr_id},
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"X-Correlation-ID": corr_id},
        )

    user_id = claims.get("user_id") or claims.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing subject",
            headers={"X-Correlation-ID": corr_id},
        )

    db = get_db()
    user_doc = await db.users.find_one({"user_id": user_id}, {"_id": 0, "password_hash": 0})
    if not user_doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
            headers={"X-Correlation-ID": corr_id},
        )

    user_doc.setdefault("role", "USER")
    user_doc.setdefault("cinema_ids", [])
    return user_doc


def require_roles(*allowed_roles: UserRole):
    async def _role_checker(
        request: Request,
        current_user: dict = Depends(get_current_user),
    ) -> dict:
        role = current_user.get("role", "USER")
        if role not in allowed_roles:
            corr_id = getattr(request.state, "correlation_id", "-")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{role}' is not authorized for this action",
                headers={"X-Correlation-ID": corr_id},
            )
        return current_user

    return _role_checker


def _to_user_response(doc: dict) -> UserResponse:
    return UserResponse(
        user_id=doc["user_id"],
        name=doc["name"],
        email=doc["email"],
        role=doc.get("role", "USER"),
        cinema_ids=doc.get("cinema_ids", []),
        created_at=doc["created_at"],
    )


@app.get("/health")
async def health():
    return {"status": "ok", "service": settings.SERVICE_NAME}


@app.post("/api/v1/auth/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def register(
    payload: RegisterRequest,
    request: Request,
    x_correlation_id: str | None = Header(default=None),
):
    corr_id = x_correlation_id or getattr(request.state, "correlation_id", "-")
    db = get_db()
    normalized_email = payload.email.strip().lower()
    user_id = f"usr_{uuid.uuid4().hex[:8]}"
    now = datetime.now(timezone.utc)

    doc = {
        "user_id": user_id,
        "name": payload.name.strip(),
        "email": normalized_email,
        "password_hash": hash_password(payload.password),
        "role": "USER",
        "cinema_ids": [],
        "created_at": now,
    }

    try:
        await db.users.insert_one(doc)
    except DuplicateKeyError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists",
            headers={"X-Correlation-ID": corr_id},
        )

    token = create_access_token(
        user_id=user_id,
        email=normalized_email,
        role="USER",
        cinema_ids=[],
    )
    logger.info(f"Registered user {user_id}", extra={"correlation_id": corr_id})

    return AuthResponse(
        access_token=token,
        user=_to_user_response(doc),
    )


@app.post("/api/v1/auth/login", response_model=AuthResponse)
async def login(
    payload: LoginRequest,
    request: Request,
    x_correlation_id: str | None = Header(default=None),
):
    corr_id = x_correlation_id or getattr(request.state, "correlation_id", "-")
    db = get_db()
    normalized_email = payload.email.strip().lower()

    user_doc = await db.users.find_one({"email": normalized_email})
    if not user_doc or not verify_password(payload.password, user_doc.get("password_hash", "")):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"X-Correlation-ID": corr_id},
        )

    user_id = user_doc["user_id"]
    role: UserRole = user_doc.get("role", "USER")
    cinema_ids: list[str] = user_doc.get("cinema_ids", [])
    token = create_access_token(
        user_id=user_id,
        email=normalized_email,
        role=role,
        cinema_ids=cinema_ids,
    )
    logger.info(f"User {user_id} ({role}) logged in", extra={"correlation_id": corr_id})

    return AuthResponse(
        access_token=token,
        user=_to_user_response(user_doc),
    )


@app.get("/api/v1/users/me", response_model=UserResponse)
async def get_me(current_user: dict = Depends(get_current_user)):
    return _to_user_response(current_user)


@app.post(
    "/api/v1/users",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
async def admin_create_user(
    payload: AdminCreateUserRequest,
    request: Request,
    _: dict = Depends(require_roles("ADMIN")),
    x_correlation_id: str | None = Header(default=None),
):
    corr_id = x_correlation_id or getattr(request.state, "correlation_id", "-")
    db = get_db()
    normalized_email = payload.email.strip().lower()
    user_id = f"usr_{uuid.uuid4().hex[:8]}"
    now = datetime.now(timezone.utc)

    doc = {
        "user_id": user_id,
        "name": payload.name.strip(),
        "email": normalized_email,
        "password_hash": hash_password(payload.password),
        "role": payload.role,
        "cinema_ids": payload.cinema_ids,
        "created_at": now,
    }

    try:
        await db.users.insert_one(doc)
    except DuplicateKeyError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists",
            headers={"X-Correlation-ID": corr_id},
        )

    logger.info(
        f"Admin created {payload.role} user {user_id}",
        extra={"correlation_id": corr_id},
    )
    return _to_user_response(doc)