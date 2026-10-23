from os import getenv
from dotenv import load_dotenv
from pathlib import Path
import logging

from fastapi import HTTPException
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker, declarative_base

load_dotenv()

primary_database_url = (
    getenv("DATABASE_URL")
    or getenv("AIVEN_DATABASE_URL")
    or getenv("MYSQL_DATABASE_URL")
)
serverless = getenv("VERCEL") == "1"
logger = logging.getLogger(__name__)


def _normalize_url(value: str):
    if value.startswith("postgres://"):
        value = value.replace("postgres://", "postgresql+psycopg://", 1)
    elif value.startswith("postgresql://"):
        value = value.replace("postgresql://", "postgresql+psycopg://", 1)
    elif value.startswith("mysql://"):
        value = value.replace("mysql://", "mysql+pymysql://", 1)
    return make_url(value)


def _create_engine(value: str):
    url = _normalize_url(value)
    options = {"pool_pre_ping": True, "echo": False}
    if url.get_backend_name() != "sqlite":
        if serverless:
            options.update(pool_size=1, max_overflow=0, pool_recycle=300)
        else:
            options.update(pool_size=5, max_overflow=10, pool_recycle=1800)

    connect_args = {}
    if url.drivername.startswith("postgresql+"):
        # Supabase's transaction pooler does not support prepared statements.
        connect_args["prepare_threshold"] = None
    elif url.get_backend_name() == "mysql":
        ca_path = getenv("DB_SSL_CA")
        if ca_path:
            resolved_ca_path = Path(ca_path)
            if not resolved_ca_path.is_file() and not resolved_ca_path.is_absolute():
                resolved_ca_path = Path(__file__).parent / resolved_ca_path.name
            ca_path = str(resolved_ca_path)
        else:
            default_ca_path = Path(__file__).with_name("ca.pem")
            ca_path = str(default_ca_path) if default_ca_path.is_file() else None
        if ca_path and Path(ca_path).is_file():
            connect_args["ssl"] = {"ca": ca_path}

    return create_engine(url, connect_args=connect_args, **options)


engine = _create_engine(primary_database_url) if primary_database_url else None
fallback_database_url = getenv("AIVEN_DATABASE_URL") or getenv("MYSQL_DATABASE_URL")
fallback_engine = (
    _create_engine(fallback_database_url)
    if fallback_database_url
    and (
        not primary_database_url
        or _normalize_url(fallback_database_url) != _normalize_url(primary_database_url)
    )
    else None
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    selected_engine = None
    for label, candidate in (("primary", engine), ("Aiven fallback", fallback_engine)):
        if candidate is None:
            continue
        try:
            with candidate.connect() as connection:
                connection.execute(text("SELECT 1"))
            selected_engine = candidate
            if label != "primary":
                logger.warning("Primary database is unreachable; using configured Aiven fallback.")
            break
        except SQLAlchemyError:
            logger.warning("Configured %s database is unreachable.", label)

    if selected_engine is None:
        raise HTTPException(status_code=503, detail="Database is currently unavailable")

    db = SessionLocal(bind=selected_engine)
    try:
        yield db
    finally:
        db.close()
