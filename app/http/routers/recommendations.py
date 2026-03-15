from fastapi import APIRouter, BackgroundTasks, Depends

from app.deps import get_recommendation_controller
from app.http.controllers.recommendations import RecommendationController
from app.http.schemas.feedback import FeedbackCreate, FeedbackRead
from app.http.schemas.recommendation import RecommendationRead, RecommendationRequest

router = APIRouter(tags=["Recommendations"])


@router.post(
    "/recommendations",
    response_model=RecommendationRead,
    status_code=201,
    summary="Gerar recomendação personalizada",
    description=(
        "Gera atividades de bem-estar personalizadas usando IA generativa. "
        "O histórico de feedback do usuário é analisado automaticamente para "
        "enriquecer o prompt e refinar as sugestões. "
        "Dispara um webhook assíncrono se `WEBHOOK_URL` estiver configurado."
    ),
)
async def create_recommendation(
    payload: RecommendationRequest,
    background_tasks: BackgroundTasks,
    controller: RecommendationController = Depends(get_recommendation_controller),
):
    return await controller.create(payload, background_tasks)


@router.post(
    "/recommendations/{recommendation_id}/feedback",
    response_model=FeedbackRead,
    status_code=201,
    summary="Enviar feedback",
    description=(
        "Registra a avaliação (1-5) do usuário para uma recomendação. "
        "O feedback alimenta o pipeline de dados que refina futuras recomendações. "
        "Dispara um webhook assíncrono se `WEBHOOK_URL` estiver configurado."
    ),
)
async def submit_feedback(
    recommendation_id: int,
    payload: FeedbackCreate,
    background_tasks: BackgroundTasks,
    controller: RecommendationController = Depends(get_recommendation_controller),
):
    return await controller.submit_feedback(recommendation_id, payload, background_tasks)
