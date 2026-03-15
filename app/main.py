import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.core.database import create_tables
from app.core.exceptions import register_exception_handlers
from app.core.logging_config import configure_logging
from app.http.routers import recommendations, users

settings = get_settings()
configure_logging(settings.log_level, settings.app_env)
logger = logging.getLogger(__name__)

_OPENAPI_TAGS = [
    {
        "name": "Users",
        "description": (
            "Cadastro e consulta de perfis de usuário. "
            "Perfis são cacheados no **Redis** (TTL 5 min) para reduzir carga no banco."
        ),
    },
    {
        "name": "Recommendations",
        "description": (
            "Geração de recomendações de bem-estar via **IA generativa** (Ollama/Anthropic). "
            "O pipeline de feedback analisa o histórico do usuário e enriquece automaticamente "
            "o prompt com preferências aprendidas. "
            "Eventos disparam **webhooks** assíncronos para integrações externas."
        ),
    },
    {
        "name": "Health",
        "description": "Endpoint de verificação de saúde do serviço.",
    },
]


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Iniciando Namu AI Wellness API", extra={"environment": settings.app_env})
    await create_tables()
    yield
    logger.info("Encerrando Namu AI Wellness API")


app = FastAPI(
    title="Namu AI — Assistente de Bem-Estar",
    description="""
API de recomendação de atividades de bem-estar personalizada com IA generativa.

## Diferenciais

| Diferencial | Implementação |
|---|---|
| **LLM containerizada** | Serviço `ollama` no docker-compose; `ollama-init` faz pull automático do modelo |
| **Fallback de parsing** | `parse_llm_response` extrai JSON de markdown, prosa ou retorna resposta padrão |
| **Validação Pydantic** | Schemas de entrada e saída com Field validators (ge/le, min_length, literal) |
| **Logging estruturado** | JSON em produção via `python-json-logger`; SQL queries em desenvolvimento |
| **Webhook** | POST assíncrono (BackgroundTask) em `recommendation.created` e `feedback.submitted` |
| **Pipeline de feedback** | Agrega ratings por categoria → injeta preferências históricas no próximo prompt |
| **Cache Redis** | Perfis de usuário cacheados com TTL 5 min; degradação graciosa se Redis indisponível |
| **Swagger automático** | Esta documentação, gerada automaticamente pelo FastAPI / OpenAPI 3.1 |

## Arquitetura para escala

- **Cache**: Redis centralizado permite múltiplas instâncias da API sem inconsistência
- **Filas**: Webhooks e pipeline podem migrar para ARQ/Celery sem mudar a interface
- **LLM**: Abstração `LLMProvider` permite trocar Ollama por Anthropic via variável de ambiente
""",
    version="1.0.0",
    openapi_tags=_OPENAPI_TAGS,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.parsed_allow_origins,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=settings.parsed_allow_headers,
)

register_exception_handlers(app)

app.include_router(users.router)
app.include_router(recommendations.router)


@app.get("/health", tags=["Health"], summary="Verificar saúde da API")
async def health_check():
    return {"status": "ok", "service": "namu-ai-wellness", "version": "1.0.0"}
