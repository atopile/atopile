import random
from fastapi import HTTPException

from atopile.database.schemas import Resistor, Inductor, Capacitor

def fetch_from_db(component: Resistor | Inductor | Capacitor):
    if random.choice([True, False]):
        ret = Resistor(**component.model_dump())
        ret.mpn = "12345"
        ret.footprint = "12345"
        return ret
    else:
        raise HTTPException(status_code=404, detail=f"Could not find a matching component")

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy import create_engine, text
import asyncio

DATABASE_URL = "postgresql+asyncpg://myuser:mypassword@localhost/resistor_db"
DATABASE_URL_SYNC = "postgresql://myuser:mypassword@localhost/resistor_db"

engine = create_async_engine(DATABASE_URL, echo=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, class_=AsyncSession)

Base = declarative_base()

async def get_db():
    async with SessionLocal() as session:
        yield session

# Synchronous engine for database creation
sync_engine = create_engine(DATABASE_URL_SYNC, echo=True)

def create_database():
    with sync_engine.connect() as conn:
        conn.execute(text("commit"))
        conn.execute(text("CREATE DATABASE resistor_db"))
        conn.execute(text("commit"))

def create_tables():
    Base.metadata.create_all(bind=sync_engine)
