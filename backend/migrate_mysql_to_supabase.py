"""Copy TeamCollab records from MySQL to an already-created Supabase schema.

Set MYSQL_DATABASE_URL and SUPABASE_MIGRATION_DATABASE_URL, then run this
script once after applying the Supabase schema migration. Target tables must be
empty; the script refuses to merge data into a populated target.
"""
import os
import sys
from pathlib import Path

from sqlalchemy import MetaData, Table, create_engine, func, insert, select, text
from sqlalchemy.engine import make_url

TABLES = ("users", "projects", "project_members", "tasks")
BATCH_SIZE = 1000


def normalize_url(value: str, target: bool = False):
    url = make_url(value)
    if url.drivername in ("mysql", "mysql+pymysql"):
        return url.set(drivername="mysql+pymysql")
    if target and url.drivername in ("postgres", "postgresql"):
        return url.set(drivername="postgresql+psycopg")
    return url


def migrate():
    source_url = os.getenv("MYSQL_DATABASE_URL")
    target_url = os.getenv("SUPABASE_MIGRATION_DATABASE_URL")
    if not source_url or not target_url:
        raise RuntimeError(
            "Set MYSQL_DATABASE_URL and SUPABASE_MIGRATION_DATABASE_URL first."
        )

    source_connect_args = {}
    ca_file = os.getenv("DB_SSL_CA")
    if ca_file and not Path(ca_file).is_file():
        local_ca = Path(__file__).with_name("ca.pem")
        if local_ca.is_file():
            ca_file = str(local_ca)
    if ca_file and Path(ca_file).is_file():
        source_connect_args["ssl"] = {"ca": ca_file}

    source = create_engine(
        normalize_url(source_url), connect_args=source_connect_args
    )
    target = create_engine(
        normalize_url(target_url, target=True),
        connect_args={"prepare_threshold": None},
        pool_pre_ping=True,
    )
    try:
        source_meta = MetaData()
        target_meta = MetaData()
        with source.connect() as source_conn:
            src_tables = {
                name: Table(name, source_meta, autoload_with=source_conn)
                for name in TABLES
            }
            with target.begin() as target_conn:
                dest_tables = {
                    name: Table(name, target_meta, schema="public", autoload_with=target_conn)
                    for name in TABLES
                }
                for name, table in dest_tables.items():
                    if target_conn.scalar(select(func.count()).select_from(table)):
                        raise RuntimeError(
                            f"Supabase table public.{name} is not empty; refusing to merge."
                        )

                for name in TABLES:
                    src_table = src_tables[name]
                    dest_table = dest_tables[name]
                    dest_columns = set(dest_table.c.keys())
                    select_columns = [
                        src_table.c[column]
                        for column in src_table.c.keys()
                        if column in dest_columns
                    ]
                    result = source_conn.execution_options(stream_results=True).execute(
                        select(*select_columns).select_from(src_table)
                    ).mappings()
                    batch = []
                    count = 0
                    for row in result:
                        batch.append(dict(row))
                        if len(batch) == BATCH_SIZE:
                            target_conn.execute(insert(dest_table), batch)
                            count += len(batch)
                            batch.clear()
                    if batch:
                        target_conn.execute(insert(dest_table), batch)
                        count += len(batch)

                    if "id" in dest_table.c:
                        sequence = target_conn.scalar(
                            text("select pg_get_serial_sequence(:table_name, 'id')"),
                            {"table_name": f"public.{name}"},
                        )
                        max_id = target_conn.scalar(select(func.max(dest_table.c.id)))
                        if sequence:
                            target_conn.execute(
                                text("select setval(cast(:sequence as regclass), :value, :called)"),
                                {
                                    "sequence": sequence,
                                    "value": max_id or 1,
                                    "called": max_id is not None,
                                },
                            )
                    print(f"Copied {count} rows from {name}")
        print("MySQL to Supabase data copy complete.")
    finally:
        source.dispose()
        target.dispose()


if __name__ == "__main__":
    try:
        migrate()
    except Exception as error:
        print(f"Migration stopped: {error}", file=sys.stderr)
        raise
