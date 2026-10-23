from pwdlib import PasswordHash

import os
from datetime import datetime, timedelta, timezone
from functools import lru_cache

import httpx
import jwt
from jwt import PyJWKClient
from jwt.exceptions import InvalidTokenError, PyJWKClientError
from dotenv import load_dotenv

password_hash = PasswordHash.recommended()

def hash_password(password: str) -> str:
    return password_hash.hash(password)

def verify_password(
        plain_password: str,
        hashed_password: str
) -> bool:
    return password_hash.verify(
        plain_password,
        hashed_password
    )


load_dotenv()

JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(
    os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "15")
)

def create_access_token(user_id: int) -> str:
    if not JWT_SECRET_KEY:
        raise RuntimeError("JWT_SECRET_KEY is not configured")

    expire = datetime.now(timezone.utc) + timedelta(
        minutes=ACCESS_TOKEN_EXPIRE_MINUTES
    )

    payload = {
        "sub": str(user_id),
        "exp": expire
    }

    return jwt.encode(
        payload,
        JWT_SECRET_KEY,
        algorithm=JWT_ALGORITHM
    )


def verify_access_token(token: str) -> dict:
    if not JWT_SECRET_KEY:
        raise RuntimeError("JWT_SECRET_KEY is not configured")

    return jwt.decode(
        token,
        JWT_SECRET_KEY,
        algorithms=[JWT_ALGORITHM]
    )

@lru_cache(maxsize=2)
def _supabase_jwks_client(supabase_url: str) -> PyJWKClient:
    return PyJWKClient(f"{supabase_url.rstrip('/')}/auth/v1/.well-known/jwks.json")


def verify_supabase_access_token(token: str) -> dict:
    supabase_url = os.getenv("SUPABASE_URL")
    if not supabase_url:
        raise RuntimeError("SUPABASE_URL is not configured")

    try:
        signing_key = _supabase_jwks_client(supabase_url).get_signing_key_from_jwt(token)
    except PyJWKClientError:
        # Older Supabase projects may still use a symmetric JWT secret and expose
        # no JWKS signing key. Ask Auth to validate those tokens over HTTPS.
        publishable_key = os.getenv("SUPABASE_PUBLISHABLE_KEY")
        if not publishable_key:
            raise
        try:
            response = httpx.get(
                f"{supabase_url.rstrip('/')}/auth/v1/user",
                headers={
                    "apikey": publishable_key,
                    "Authorization": f"Bearer {token}",
                },
                timeout=5.0,
            )
            if response.status_code == 401:
                raise InvalidTokenError("Supabase rejected the access token")
            response.raise_for_status()
            auth_user = response.json()
        except httpx.HTTPError as error:
            raise PyJWKClientError("Could not validate the Supabase access token") from error
        return {
            "sub": auth_user["id"],
            "email": auth_user.get("email"),
            "user_metadata": auth_user.get("user_metadata") or {},
            "aud": "authenticated",
        }

    return jwt.decode(
        token,
        signing_key.key,
        algorithms=["ES256", "RS256"],
        audience="authenticated",
        issuer=f"{supabase_url.rstrip('/')}/auth/v1",
    )
