from pydantic import BaseModel
from sqlalchemy import Column, Integer, String
from app.database.database import Base

class Fact(Base):
    __tablename__ = "facts"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    description = Column(String, nullable=False)
    source = Column(String, nullable=False)
    category = Column(String, nullable=False)

class FactCreate(BaseModel):
    title: str
    description: str
    source: str
    category: str

class FactUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    source: str | None = None
    category: str | None = None
