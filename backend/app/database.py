"""SQLAlchemy engine and SessionLocal for PostgreSQL."""
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.config import DATABASE_URL

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    echo=False,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """Dependency: yield a DB session for FastAPI."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def check_db():
    """Run SELECT 1 to verify database connectivity. Returns True on success."""
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    return True
