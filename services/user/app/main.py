from contextlib import asynccontextmanager
from datetime import datetime, timezone
import logging
import uuid
from fastapi import Depends, FastAPI, Header, HTTPException, Request, Response, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
import jwt
from pymongo.errors import DuplicateKeyError
from .config import settings
from .database import close_db, connect_db, get_db
from .models import AuthResponse, LoginRequest, RegisterRequest, UserResponse
from .security import create_access_token, decode_access_token, hash_password, verify_password

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


@asynccontextmanager
async def lifespan(_: FastAPI):
    await connect_db()
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
):
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
    return user_doc


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

    token = create_access_token(user_id=user_id, email=normalized_email, role="USER")
    logger.info(f"Registered user {user_id}", extra={"correlation_id": corr_id})

    return AuthResponse(
        access_token=token,
        user=UserResponse(
            user_id=user_id,
            name=doc["name"],
            email=normalized_email,
            role="USER",
            created_at=now,
        ),
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
    role = user_doc.get("role", "USER")
    token = create_access_token(user_id=user_id, email=normalized_email, role=role)
    logger.info(f"User {user_id} logged in", extra={"correlation_id": corr_id})

    return AuthResponse(
        access_token=token,
        user=UserResponse(
            user_id=user_id,
            name=user_doc["name"],
            email=normalized_email,
            role=role,
            created_at=user_doc["created_at"],
        ),
    )


@app.get("/api/v1/users/me", response_model=UserResponse)
async def get_me(current_user: dict = Depends(get_current_user)):
    return UserResponse(**current_user)