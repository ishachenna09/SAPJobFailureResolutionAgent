from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base
from app.config import settings

# For SQLite, enable check_same_thread=False
connect_args = {"check_same_thread": False} if settings.DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(
    settings.DATABASE_URL,
    connect_args=connect_args,
    echo=False
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def ensure_sqlite_columns(engine):
    """
    Ensures existing SQLite databases are seamlessly upgraded with Phase 2 columns
    without throwing 'no such column' errors.
    """
    if not settings.DATABASE_URL.startswith("sqlite"):
        return
    with engine.begin() as conn:
        # Check platform columns across tables
        tables_to_check = ["jobs", "job_runs", "job_events", "failure_analyses", "remediation_executions"]
        for table in tables_to_check:
            try:
                res = conn.execute(text(f"PRAGMA table_info({table})")).fetchall()
                if res:
                    existing_cols = {row[1] for row in res}
                    if "platform" not in existing_cols:
                        conn.execute(text(f"ALTER TABLE {table} ADD COLUMN platform VARCHAR(50) DEFAULT 'MOCK_SAP'"))
            except Exception as e:
                print(f"Migration notice ({table} platform): {e}")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
