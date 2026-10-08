from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from app.config import get_settings

class Base(DeclarativeBase):
    pass

engine = create_engine(
    get_settings().database_url,
    pool_pre_ping=True,
    pool_size=3,
    max_overflow=0,
    pool_recycle=1800,
    future=True,
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
