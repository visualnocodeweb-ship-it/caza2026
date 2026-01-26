import os
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

# PostgreSQL database URL from environment variable
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("La variable de entorno DATABASE_URL no está configurada. La aplicación no puede iniciar.")

# Adjust the URL for the psycopg (v3) driver
if DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg://", 1)

# Create the SQLAlchemy engine for PostgreSQL
engine = create_engine(DATABASE_URL)

# Each instance of the Base class will be a SQLAlchemy model
Base = declarative_base()

# Define the Establishment model
class Establishment(Base):
    __tablename__ = "establishments"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=True)
    owner_email = Column(String, index=True, nullable=True)
    cuit = Column(String, index=True, nullable=True)
    address = Column(String, nullable=True)
    payment_link = Column(String, nullable=True) # New field for Mercado Pago payment link
    pdf_path = Column(String, nullable=True) # New field for PDF path
    webhook_data = Column(Text, nullable=True) # Store complete webhook data as JSON
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False) # Timestamp of creation

# Define the Price model
class Price(Base):
    __tablename__ = "prices"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    value = Column(Integer, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

# Session maker
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Function to create the database tables
def create_db_and_tables():
    Base.metadata.create_all(bind=engine)

# Dependency to get the database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()