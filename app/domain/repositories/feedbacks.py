from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models.feedback import Feedback


class FeedbackRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, data: dict) -> Feedback:
        feedback = Feedback(**data)
        self.session.add(feedback)
        try:
            await self.session.commit()
            await self.session.refresh(feedback)
        except IntegrityError:
            await self.session.rollback()
            raise
        except SQLAlchemyError:
            await self.session.rollback()
            raise
        return feedback
