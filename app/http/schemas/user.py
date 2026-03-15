from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

ExperienceLevel = Literal["iniciante", "intermediário", "avançado"]


class UserCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    age: int = Field(..., ge=1, le=120)
    goals: list[str] = Field(..., min_length=1)
    restrictions: str | None = None
    experience_level: ExperienceLevel


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    age: int
    goals: list[str]
    restrictions: str | None
    experience_level: str
    created_at: datetime
