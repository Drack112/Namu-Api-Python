from sqlalchemy import Column, DateTime, Integer, String, Text
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    age = Column(Integer, nullable=False)
    goals = Column(ARRAY(Text), nullable=False)
    restrictions = Column(Text, nullable=True)
    experience_level = Column(String(50), nullable=False)
    created_at = Column(DateTime, server_default=func.now())

    recommendations = relationship("Recommendation", back_populates="user")
