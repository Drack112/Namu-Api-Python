from fastapi import HTTPException

from app.core.exceptions.errors import NotFoundError
from app.domain.models.user import User
from app.domain.services.users import UserService
from app.http.schemas.user import UserCreate


class UserController:
    def __init__(self, service: UserService):
        self.service = service

    async def create(self, payload: UserCreate) -> User:
        return await self.service.create(payload)

    async def get_by_id(self, user_id: int) -> User:
        try:
            return await self.service.get_by_id(user_id)
        except NotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
