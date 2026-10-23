from fastapi import APIRouter, Depends, HTTPException, Request, Response, Security
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from database import get_db
from models import UserDB
from schemas import UserCreate, UserResponse, UserLogin, RegistrationAttempt
from security import (
    hash_password, verify_password, create_access_token, verify_access_token,
    verify_supabase_access_token,
)
from jwt.exceptions import InvalidTokenError, PyJWKClientError
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from rate_limits import (
    LOGIN_LIMIT,
    READ_LIMIT,
    REGISTRATION_LIMIT,
    WRITE_LIMIT,
    consume_limit,
)

router = APIRouter(
    prefix="/auth",
    tags=["Authentication"]
)


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=201
)
def register_user(
    user: UserCreate,
    request: Request,
    db: Session = Depends(get_db),
):
    email = str(user.email).strip().lower()
    ip_address = request.client.host if request.client else "unknown"
    consume_limit(db, "registration-email", email, REGISTRATION_LIMIT)
    consume_limit(db, "registration-ip", ip_address, REGISTRATION_LIMIT)

    new_user = UserDB(
        name=user.name,
        email=email,
        password_hash=hash_password(user.password)
    )

    try:
        db.add(new_user)
        db.commit()
        db.refresh(new_user)

    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="An account with this email may already exist"
        )

    return new_user


@router.post("/registration-attempt", status_code=204)
def authorize_registration_attempt(
    attempt: RegistrationAttempt,
    request: Request,
    db: Session = Depends(get_db),
):
    """Reserve a signup attempt before the browser asks Supabase to email."""
    email = str(attempt.email).strip().lower()
    ip_address = request.client.host if request.client else "unknown"
    consume_limit(db, "supabase-registration-email", email, REGISTRATION_LIMIT)
    consume_limit(db, "supabase-registration-ip", ip_address, REGISTRATION_LIMIT)


@router.post("/login")
def login_user(
    user: UserLogin,
    request: Request,
    db: Session = Depends(get_db),
):
    email = str(user.email).strip().lower()
    ip_address = request.client.host if request.client else "unknown"
    consume_limit(db, "login-email", email, LOGIN_LIMIT)
    consume_limit(db, "login-ip", ip_address, LOGIN_LIMIT)

    existing_user = db.query(UserDB).filter(
        UserDB.email == email
    ).first()

    if (
        existing_user is None
        or existing_user.password_hash.startswith("$supabase$")
        or not verify_password(user.password, existing_user.password_hash)
    ):
        raise HTTPException(
            status_code = 401,
            detail = "Invalid email or password"
        )

    if not existing_user.is_active:
        raise HTTPException(
            status_code = 403,
            detail = "Account is inactive"
        )

    access_token = create_access_token(existing_user.id)

    return {
        "access_token": access_token,
        "token_type": "bearer"
    }


bearer_scheme = HTTPBearer()


def get_verified_claims(
    credentials: HTTPAuthorizationCredentials = Security(bearer_scheme),
):
    token = credentials.credentials
    try:
        payload = verify_access_token(token)
        return {"kind": "local", "claims": payload}
    except (InvalidTokenError, RuntimeError, KeyError, TypeError, ValueError):
        try:
            return {"kind": "supabase", "claims": verify_supabase_access_token(token)}
        except (
            InvalidTokenError,
            PyJWKClientError,
            RuntimeError,
            KeyError,
            TypeError,
            ValueError,
        ):
            raise HTTPException(
                status_code=401,
                detail="Invalid or expired token",
                headers={"WWW-Authenticate": "Bearer"},
            )


def get_current_user(
    verified: dict = Depends(get_verified_claims),
    db: Session = Depends(get_db),
):
    payload = verified["claims"]
    try:
        if verified["kind"] == "local":
            user_id = int(payload["sub"])
        else:
            auth_user_id = str(payload["sub"])
            email = payload.get("email")
            if not email:
                raise InvalidTokenError("Supabase token has no email claim")

            user = db.query(UserDB).filter(UserDB.auth_user_id == auth_user_id).first()
            if user is None:
                user = db.query(UserDB).filter(UserDB.email == email).first()
                if user is not None and user.auth_user_id not in (None, auth_user_id):
                    raise InvalidTokenError("Email is already linked to another Auth user")
                if user is None:
                    metadata = payload.get("user_metadata") or {}
                    user = UserDB(
                        name=metadata.get("name") or email.split("@")[0],
                        email=email,
                        password_hash="$supabase$",
                        auth_user_id=auth_user_id,
                    )
                    db.add(user)
                else:
                    user.auth_user_id = auth_user_id
                db.commit()
                db.refresh(user)
            user_id = user.id
    except (InvalidTokenError, PyJWKClientError, RuntimeError, KeyError, TypeError, ValueError):
        db.rollback()
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"}
        )

    user = db.query(UserDB).filter(UserDB.id == user_id).first()

    if user is None or not user.is_active:
        raise HTTPException(
            status_code=401,
            detail="Invalid or inactive user",
            headers={"WWW-Authenticate": "Bearer"}
        )

    return user


def enforce_user_rate_limit(
    request: Request,
    response: Response,
    verified: dict = Depends(get_verified_claims),
    db: Session = Depends(get_db),
):
    subject = verified["claims"].get("sub")
    if not subject:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    is_read = request.method in {"GET", "HEAD"}
    limit = READ_LIMIT if is_read else WRITE_LIMIT
    scope = "database-read" if is_read else "database-write"
    remaining, retry_after = consume_limit(
        db,
        scope,
        f"{verified['kind']}:{subject}",
        limit,
    )
    response.headers["X-RateLimit-Limit"] = str(limit)
    response.headers["X-RateLimit-Remaining"] = str(remaining)
    response.headers["X-RateLimit-Reset-After"] = str(retry_after)


@router.get(
    "/me",
    response_model=UserResponse,
    dependencies=[Depends(enforce_user_rate_limit)],
)
def read_current_user(
    current_user: UserDB = Depends(get_current_user)
):
    return current_user
