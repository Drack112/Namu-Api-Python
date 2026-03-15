from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.http.schemas.feedback import FeedbackRead


class Activity(BaseModel):
    name: str
    description: str
    duration: str
    category: str


class RecommendationRequest(BaseModel):
    user_id: int
    context: str | None = Field(
        None,
        description="Contexto adicional do dia, ex: 'estou com dor nas costas hoje'",
    )


class RecommendationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    context: str | None
    activities: list[Activity]
    reasoning: str
    precautions: list[str]
    created_at: datetime
    feedback: FeedbackRead | None = None


class RecommendationHistoryItem(BaseModel):
    id: int
    user_id: int
    context: str | None
    activities: list[Activity]
    reasoning: str
    precautions: list[str]
    created_at: datetime
    feedback_rating: int | None = None
    feedback_comment: str | None = None
