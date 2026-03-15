from sqlalchemy import CheckConstraint, Column, DateTime, ForeignKey, Integer, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class Feedback(Base):
    __tablename__ = "feedbacks"

    id = Column(Integer, primary_key=True, index=True)
    recommendation_id = Column(
        Integer,
        ForeignKey("recommendations.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    rating = Column(Integer, nullable=False)
    comment = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    __table_args__ = (CheckConstraint("rating >= 1 AND rating <= 5", name="ck_feedback_rating"),)

    recommendation = relationship("Recommendation", back_populates="feedback")
