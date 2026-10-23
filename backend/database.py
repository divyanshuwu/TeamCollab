from os import getenv
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker, declarative_base

load_dotenv()

database_url = getenv("DATABASE_URL")
if not database_url:
    raise RuntimeError("DATABASE_URL is not configured")

# Supabase transaction pooler (used by Vercel) requires prepared statements off.
if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql+psycopg://", 1)
elif database_url.startswith("postgresql://"):
    database_url = database_url.replace("postgresql://", "postgresql+psycopg://", 1)

database_url = make_url(database_url)

serverless = getenv("VERCEL") == "1"
engine_options = {"pool_pre_ping": True, "echo": False}
if database_url.get_backend_name() != "sqlite":
    if serverless:
        engine_options.update(pool_size=1, max_overflow=0, pool_recycle=300)
    else:
        engine_options.update(pool_size=5, max_overflow=10, pool_recycle=1800)

connect_args = (
    {"prepare_threshold": None}
    if database_url.drivername.startswith("postgresql+")
    else {}
)
engine = create_engine(
    database_url,
    connect_args=connect_args,
    **engine_options,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
