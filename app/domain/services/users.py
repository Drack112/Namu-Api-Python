import logging
from types import SimpleNamespace

from app.core.exceptions.errors import NotFoundError
from app.domain.models.user import User
from app.domain.repositories.users import UserRepository
from app.http.schemas.user import UserCreate
from app.infra import cache

logger = logging.getLogger(__name__)


class UserService:
    def __init__(self, repo: UserRepository):
        self.repo = repo

    async def create(self, payload: UserCreate) -> User:
        user = await self.repo.create(payload.model_dump())
        logger.info("User created", extra={"user_id": user.id, "user_name": user.name})
        await cache.cache_set(
            cache.user_cache_key(user.id),
            {
                "id": user.id,
                "name": user.name,
                "age": user.age,
                "goals": user.goals,
                "restrictions": user.restrictions,
                "experience_level": user.experience_level,
                "created_at": user.created_at.isoformat() if user.created_at else None,
            },
        )
        return user

    async def get_by_id(self, user_id: int) -> User | SimpleNamespace:
        cached = await cache.cache_get(cache.user_cache_key(user_id))
        if cached:
            logger.debug("User served from cache", extra={"user_id": user_id})
            return SimpleNamespace(**cached)

        user = await self.repo.get_by_id(user_id)
        if not user:
            raise NotFoundError("Usuário")

        await cache.cache_set(
            cache.user_cache_key(user_id),
            {
                "id": user.id,
                "name": user.name,
                "age": user.age,
                "goals": user.goals,
                "restrictions": user.restrictions,
                "experience_level": user.experience_level,
                "created_at": user.created_at.isoformat() if user.created_at else None,
            },
        )
        return user
