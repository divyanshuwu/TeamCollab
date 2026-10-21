from fastapi import APIRouter, Depends, HTTPException, Security
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from database import get_db
from models import UserDB
from schemas import UserCreate, UserResponse, UserLogin
from security import hash_password, verify_password, create_access_token, verify_access_token
from jwt.exceptions import InvalidTokenError
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

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
    db: Session = Depends(get_db)
):
    new_user = UserDB(
        name=user.name,
        email=str(user.email),
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


@router.post("/login")
def login_user(
    user: UserLogin,
    db: Session = Depends(get_db)
):
    existing_user = db.query(UserDB).filter(
        UserDB.email == str(user.email)
    ).first()

    if (
        existing_user is None
        or not verify_password(
            user.password,
            existing_user.password_hash
        )
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


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Security(bearer_scheme),
    db: Session = Depends(get_db)
):
    token = credentials.credentials

    try:
        payload = verify_access_token(token)
        user_id = int(payload["sub"])
    except (InvalidTokenError, KeyError, TypeError, ValueError):
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"}
        )

    user = db.query(UserDB).filter(
        UserDB.id == user_id
    ).first()

    if user is None or not user.is_active:
        raise HTTPException(
            status_code=401,
            detail="Invalid or inactive user",
            headers={"WWW-Authenticate": "Bearer"}
        )

    return user

@router.get("/me", response_model=UserResponse)
def read_current_user(
    current_user: UserDB = Depends(get_current_user)
):
    return current_user