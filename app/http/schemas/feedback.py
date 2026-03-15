from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class FeedbackCreate(BaseModel):
    rating: int = Field(..., ge=1, le=5, description="Avaliação de 1 a 5")
    comment: str | None = Field(None, description="Comentário opcional")


class FeedbackRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    recommendation_id: int
    rating: int
    comment: str | None
    created_at: datetime
