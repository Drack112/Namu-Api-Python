from sqlalchemy import Column, DateTime, ForeignKey, Integer, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class Recommendation(Base):
    __tablename__ = "recommendations"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    context = Column(Text, nullable=True)
    activities = Column(JSONB, nullable=False)
    reasoning = Column(Text, nullable=False)
    precautions = Column(JSONB, nullable=False, default=list)
    created_at = Column(DateTime, server_default=func.now())

    user = relationship("User", back_populates="recommendations")
    feedback = relationship("Feedback", back_populates="recommendation", uselist=False)
