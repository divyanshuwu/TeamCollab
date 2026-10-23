"""Database-backed two-hour limits shared across Vercel function instances."""

from datetime import datetime, timedelta
import hashlib
import hmac
import os
import secrets

from fastapi import HTTPException
from sqlalchemy import case, delete, select
from sqlalchemy.dialects.mysql import insert as mysql_insert
from sqlalchemy.dialects.postgresql import insert as postgres_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from models import RateLimitDB


WINDOW = timedelta(hours=2)
READ_LIMIT = int(os.getenv("DB_READ_LIMIT_2H", "300"))
WRITE_LIMIT = int(os.getenv("DB_WRITE_LIMIT_2H", "60"))
REGISTRATION_LIMIT = int(os.getenv("REGISTRATION_LIMIT_2H", "3"))
LOGIN_LIMIT = int(os.getenv("LOGIN_LIMIT_2H", "10"))


def _key_hash(scope: str, identity: str) -> str:
    secret = os.getenv("RATE_LIMIT_HMAC_KEY") or os.getenv("JWT_SECRET_KEY")
    if not secret:
        raise HTTPException(
            status_code=503,
            detail="Rate limiting is not configured",
        )
    message = f"{scope}:{identity}".encode("utf-8")
    return hmac.new(secret.encode("utf-8"), message, hashlib.sha256).hexdigest()


def consume_limit(db: Session, scope: str, identity: str, limit: int) -> tuple[int, int]:
    """Atomically count one request and return (remaining, retry-after seconds)."""
    if limit < 1:
        raise HTTPException(status_code=503, detail="Rate limit configuration is invalid")

    key_hash = _key_hash(scope, identity)
    table = RateLimitDB.__table__
    now = datetime.utcnow()
    expired = table.c.window_started_at <= now - WINDOW
    values = {
        "key_hash": key_hash,
        "window_started_at": now,
        "request_count": 1,
    }

    try:
        # Opportunistically remove abandoned counters without depending on
        # process-local timers that do not survive serverless invocations.
        if secrets.randbelow(100) == 0:
            db.execute(
                delete(table).where(
                    table.c.window_started_at <= now - (WINDOW * 2)
                )
            )

        dialect = db.get_bind().dialect.name
        if dialect == "postgresql":
            insert = postgres_insert(table).values(**values)
            statement = insert.on_conflict_do_update(
                index_elements=[table.c.key_hash],
                set_={
                    "window_started_at": case(
                        (expired, now), else_=table.c.window_started_at
                    ),
                    "request_count": case(
                        (expired, 1), else_=table.c.request_count + 1
                    ),
                },
            ).returning(table.c.request_count, table.c.window_started_at)
            count, window_started = db.execute(statement).one()
        elif dialect == "sqlite":
            insert = sqlite_insert(table).values(**values)
            statement = insert.on_conflict_do_update(
                index_elements=[table.c.key_hash],
                set_={
                    "window_started_at": case(
                        (expired, now), else_=table.c.window_started_at
                    ),
                    "request_count": case(
                        (expired, 1), else_=table.c.request_count + 1
                    ),
                },
            ).returning(table.c.request_count, table.c.window_started_at)
            count, window_started = db.execute(statement).one()
        elif dialect == "mysql":
            insert = mysql_insert(table).values(**values)
            statement = insert.on_duplicate_key_update(
                request_count=case(
                    (expired, 1), else_=table.c.request_count + 1
                ),
                window_started_at=case(
                    (expired, insert.inserted.window_started_at),
                    else_=table.c.window_started_at,
                ),
            )
            db.execute(statement)
            row = db.execute(
                select(table.c.request_count, table.c.window_started_at)
                .where(table.c.key_hash == key_hash)
                .with_for_update()
            ).one()
            count, window_started = row
        else:
            raise HTTPException(
                status_code=503,
                detail="Database driver does not support atomic rate limits",
            )

        db.commit()
    except HTTPException:
        db.rollback()
        raise
    except SQLAlchemyError as error:
        db.rollback()
        # Fail closed: a missing migration or failed counter write must not
        # silently disable the protection.
        raise HTTPException(
            status_code=503,
            detail="Database rate limiting is unavailable",
        ) from error

    reset_at = window_started + WINDOW
    retry_after = max(1, int((reset_at - now).total_seconds()))
    remaining = max(0, limit - count)
    if count > limit:
        raise HTTPException(
            status_code=429,
            detail="Request limit reached. Try again after the two-hour window resets.",
            headers={"Retry-After": str(retry_after)},
        )
    return remaining, retry_after
