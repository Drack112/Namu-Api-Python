from fastapi import APIRouter, Depends

from app.deps import get_recommendation_controller, get_user_controller
from app.http.controllers.recommendations import RecommendationController
from app.http.controllers.users import UserController
from app.http.schemas.recommendation import RecommendationHistoryItem
from app.http.schemas.user import UserCreate, UserRead

router = APIRouter(prefix="/users", tags=["Users"])


@router.post(
    "/",
    response_model=UserRead,
    status_code=201,
    summary="Criar usuário",
    description="Cadastra um novo perfil. O perfil é armazenado no banco **e** populado no cache Redis imediatamente.",
)
async def create_user(
    payload: UserCreate,
    controller: UserController = Depends(get_user_controller),
):
    return await controller.create(payload)


@router.get(
    "/{user_id}",
    response_model=UserRead,
    summary="Buscar usuário",
    description="Retorna o perfil do usuário. Resposta servida do **cache Redis** quando disponível (TTL 5 min).",
)
async def get_user(
    user_id: int,
    controller: UserController = Depends(get_user_controller),
):
    return await controller.get_by_id(user_id)


@router.get(
    "/{user_id}/recommendations",
    response_model=list[RecommendationHistoryItem],
    summary="Histórico de recomendações",
    description="Lista todas as recomendações do usuário com ratings de feedback associados.",
)
async def get_user_recommendations(
    user_id: int,
    controller: RecommendationController = Depends(get_recommendation_controller),
):
    return await controller.get_user_recommendations(user_id)
