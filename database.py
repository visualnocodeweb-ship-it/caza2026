from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# SQLite database URL
DATABASE_URL = "sqlite:///./sql_app.db"

# Create the SQLAlchemy engine
engine = create_engine(
    DATABASE_URL, connect_args={"check_same_thread": False}
)

# Each instance of the Base class will be a SQLAlchemy model
Base = declarative_base()

# Define the Establishment model
class Establishment(Base):
    __tablename__ = "establishments"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=True)
    owner_email = Column(String, unique=True, index=True, nullable=True)
    cuit = Column(String, unique=True, index=True, nullable=True)
    address = Column(String, nullable=True)
    payment_link = Column(String, nullable=True) # New field for Mercado Pago payment link
    pdf_path = Column(String, nullable=True) # New field for PDF path

# Create the database tables
def create_db_and_tables():
    Base.metadata.create_all(bind=engine)

# Dependency to get the database session
def get_db():
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

