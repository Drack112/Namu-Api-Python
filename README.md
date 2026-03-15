# Namu AI — Assistente de Bem-Estar

API de recomendação de atividades de bem-estar personalizada com IA generativa. A partir do perfil do usuário (objetivos, restrições físicas, nível de experiência) e de um contexto opcional do dia, o sistema consulta um LLM e retorna um plano de atividades estruturado com raciocínio e precauções.

---

## Funcionalidades

- **Cadastro de usuários** com perfil completo: nome, idade, objetivos, restrições e nível de experiência
- **Geração de recomendações** personalizadas via LLM (Anthropic Claude ou Ollama)
- **Contexto diário opcional** — o usuário informa como está se sentindo para refinar a recomendação
- **Pipeline de feedback** — avaliações são analisadas e preferências históricas são injetadas no próximo prompt
- **Webhook de eventos** — notificação assíncrona de sistemas externos em `recommendation.created` e `feedback.submitted`
- **Cache Redis** de perfis de usuário com TTL de 5 minutos e degradação graciosa
- **Histórico de recomendações** com JOIN de feedback em uma única query SQL
- **Feedback por recomendação** com nota de 1 a 5 e comentário opcional
- **Validação de entrada em pt-BR** — mensagens de erro traduzidas para o usuário final
- **Logs estruturados em JSON** com níveis distintos por ambiente
- **Tratamento de erros centralizado** com respostas padronizadas (`status_code`, `path`, `message`)
- **Dois provedores de LLM** selecionáveis via variável de ambiente, sem alterar código
- **Documentação interativa** (Swagger/OpenAPI) gerada automaticamente em `/docs`

---

## Tecnologias

| Tecnologia            | Versão | Por que foi escolhida                                                      |
| --------------------- | ------ | -------------------------------------------------------------------------- |
| **FastAPI**           | 0.115  | Alta performance async, OpenAPI automático, injeção de dependências nativa |
| **SQLAlchemy**        | 2.0    | ORM assíncrono com suporte a `asyncpg`, queries tipadas                    |
| **asyncpg**           | 0.30   | Driver PostgreSQL nativo e assíncrono, melhor performance que psycopg2     |
| **Pydantic v2**       | 2.12   | Validação e serialização de dados com performance nativa em Rust           |
| **pydantic-settings** | 2.7    | Carregamento de configurações via env com validação automática             |
| **Redis**             | 5.2    | Cache em memória para perfis de usuário; degradação graciosa se indisponível |
| **Anthropic SDK**     | 0.44   | Cliente oficial para o Claude com suporte assíncrono                       |
| **Ollama**            | —      | Execução local de LLMs open-source; containerizado junto com a API        |
| **httpx**             | 0.28   | Cliente HTTP assíncrono para chamadas ao Ollama e webhooks                 |
| **pytest + pytest-asyncio** | latest | Testes assíncronos com suporte a fixtures de banco real             |
| **Ruff + Black**      | latest | Linting e formatação rápidos e consistentes em todo o projeto              |

---

## Instalação e execução

### Pré-requisitos

- Docker e Docker Compose
- Python 3.12+ (para execução local sem Docker)

### Com Docker (recomendado)

O `docker compose up` sobe **quatro serviços** automaticamente: PostgreSQL, Redis, Ollama e a API.
O serviço `ollama-init` realiza o `ollama pull` do modelo configurado antes de a API iniciar.

```bash
# 1. Clone o repositório
git clone <url-do-repositorio>
cd teste-soma

# 2. Crie o arquivo de variáveis de ambiente
cp .env.example .env
# Edite o .env conforme necessário (LLM_PROVIDER, LLM_API_KEY, etc.)

# 3. Suba todos os serviços
docker compose up --build
```

A API estará disponível em `http://localhost:8000`.
A documentação interativa estará em `http://localhost:8000/docs`.

### Execução local (sem Docker)

```bash
# 1. Crie e ative o ambiente virtual
python -m venv .venv
source .venv/bin/activate

# 2. Instale as dependências
pip install -r requirements.txt

# 3. Suba o banco e o Redis
docker compose up postgres redis -d

# 4. Configure as variáveis de ambiente
cp .env.example .env

# 5. Inicie a API
uvicorn app.main:app --reload
```

> Para usar Ollama localmente, instale-o em [ollama.com](https://ollama.com), execute `ollama pull llama3` e defina `LLM_PROVIDER=ollama` no `.env`. O `OLLAMA_BASE_URL` padrão aponta para `http://localhost:11434`.

### Variáveis de ambiente

| Variável          | Padrão                       | Descrição                                       |
| ----------------- | ---------------------------- | ----------------------------------------------- |
| `APP_ENV`         | `development`                | Ambiente (`development` ou `production`)        |
| `LOG_LEVEL`       | `DEBUG`                      | Nível de log                                    |
| `DB_HOST`         | `localhost`                  | Host do PostgreSQL                              |
| `DB_PORT`         | `5432`                       | Porta do PostgreSQL                             |
| `DB_USER`         | `namu`                       | Usuário do banco                                |
| `DB_PASSWORD`     | `namu123`                    | Senha do banco                                  |
| `DB_NAME`         | `namu_ai`                    | Nome do banco                                   |
| `REDIS_URL`       | `redis://localhost:6379`     | URL do Redis para cache                         |
| `WEBHOOK_URL`     | _(vazio)_                    | URL de destino dos eventos; deixe vazio para desabilitar |
| `LLM_PROVIDER`    | `anthropic`                  | Provedor LLM (`anthropic` ou `ollama`)          |
| `LLM_API_KEY`     | —                            | API key da Anthropic                            |
| `LLM_MODEL`       | `claude-haiku-4-5-20251001`  | Modelo Anthropic a utilizar                     |
| `OLLAMA_BASE_URL` | `http://localhost:11434`     | URL base do Ollama                              |
| `OLLAMA_MODEL`    | `llama3`                     | Modelo Ollama a utilizar                        |
| `ALLOW_ORIGINS`   | `http://localhost:3000`      | Origens CORS permitidas (separadas por vírgula) |
| `ALLOW_HEADERS`   | `Content-Type,Authorization` | Headers CORS permitidos (separados por vírgula) |

> Em `production`, as variáveis **não são lidas de arquivo `.env`** — devem estar no ambiente do shell.

### Dados de exemplo

O banco é populado automaticamente no primeiro start com 5 perfis de usuário:

| ID  | Nome           | Perfil                                    |
| --- | -------------- | ----------------------------------------- |
| 1   | Ana Costa      | Iniciante, foco em estresse e sono        |
| 2   | Bruno Lima     | Intermediário, restrição no joelho        |
| 3   | Carla Mendes   | Intermediária, gestante de 5 meses        |
| 4   | Diego Ferreira | Avançado, foco em hipertrofia             |
| 5   | Elena Souza    | Iniciante, 60 anos, artrite e hipertensão |

### Testando a API

Importe `docs/insomnia_collection.json` no [Insomnia](https://insomnia.rest) ou use o Swagger em `/docs`.

---

## Decisões técnicas

### Arquitetura em camadas

```
Router → Controller → Service → Repository
```

- **Router**: recebe a requisição HTTP, injeta `BackgroundTasks` para webhooks assíncronos
- **Controller**: converte erros de domínio em `HTTPException` com status codes corretos
- **Service**: contém a lógica de negócio; não conhece HTTP; executa o pipeline de feedback antes do LLM
- **Repository**: único ponto de acesso ao banco; faz rollback em caso de erro

### Estrutura de pastas

```
app/
├── core/          configurações, banco de dados, logging, exceções HTTP
├── domain/
│   ├── models/    entidades SQLAlchemy
│   ├── services/  lógica de negócio + pipeline de feedback
│   └── repositories/  acesso ao banco
├── http/
│   ├── schemas/   modelos Pydantic de entrada e saída
│   ├── controllers/  mapeamento de erros para HTTP
│   └── routers/   endpoints FastAPI
└── infra/
    ├── cache.py   Redis com degradação graciosa
    ├── webhook.py notificações HTTP assíncronas
    └── llm/       provedores de LLM (Anthropic, Ollama) com interface comum
```

### Pipeline de feedback

Antes de cada chamada ao LLM, o `RecommendationService` chama `build_feedback_context(user_id, session)`:

1. Consulta todas as avaliações do usuário com JOIN nas atividades recomendadas
2. Agrupa ratings por categoria de atividade
3. Categorias com ≥ 2 avaliações e média ≥ 4 são marcadas como "preferidas"
4. O resultado é injetado no prompt como seção `PREFERÊNCIAS HISTÓRICAS`

Com isso, o modelo aprende progressivamente o que funciona para cada usuário sem nenhum dado extra armazenado — o banco de feedbacks existente é suficiente.

### Cache Redis

Perfis de usuário são armazenados no Redis com TTL de 5 minutos. Se o Redis estiver indisponível, todas as operações de cache falham silenciosamente e a requisição cai para o banco normalmente — sem impacto para o usuário final.

### Webhook

Após `recommendation.created` e `feedback.submitted`, o serviço dispara um `POST` JSON para `WEBHOOK_URL` como `BackgroundTask` do FastAPI — a resposta HTTP já foi enviada antes da chamada ao webhook. Falhas de rede são logadas como `WARNING` e não afetam o fluxo principal.

Formato do payload:

```json
{
  "event": "recommendation.created",
  "timestamp": "2026-03-15T18:00:00+00:00",
  "data": { "recommendation_id": 42, "user_id": 7 }
}
```

### Abstração do LLM

`AnthropicProvider` e `OllamaProvider` implementam a mesma interface. A seleção ocorre via `LLM_PROVIDER` em tempo de execução. O parse da resposta usa três estratégias em cascata (JSON puro → cerca de markdown → regex de chaves) com fallback para uma atividade segura padrão, garantindo que o endpoint nunca retorne erro por causa de formatação inesperada do modelo.

### Logging estruturado

- **Development**: nível `DEBUG`, JSON estruturado, queries SQL visíveis
- **Production**: nível mínimo `WARNING`, sem leitura de `.env`

### Resposta padronizada de erros

```json
{
  "status_code": 404,
  "path": "/users/99",
  "message": "Usuário não encontrado",
  "details": []
}
```

Erros de validação do Pydantic são traduzidos para pt-BR antes de chegar ao cliente.

### Arquitetura para escala

| Componente | Hoje | Caminho de escala |
|---|---|---|
| Cache | Redis single-node | Redis Cluster / ElastiCache |
| Webhooks | `BackgroundTask` in-process | Fila ARQ/Celery + worker dedicado |
| Pipeline de feedback | Síncrono na requisição | Worker que pré-computa e armazena no Redis |
| LLM | Chamada direta por request | Pool de workers + queue para evitar sobrecarga |

---

## Testes

```bash
# Suba o banco de teste
docker compose up postgres -d

# Rode a suíte completa
pytest tests/ -v
```

| Camada | Arquivos | O que cobre |
|---|---|---|
| **Unit** | `tests/unit/` | prompts, error handlers, Ollama provider, cache, webhook, pipeline |
| **Integration** | `tests/integration/` | repositories, services e pipeline com banco real |
| **E2E** | `tests/e2e/` | endpoints HTTP completos incluindo webhook e casos de erro |

O CI (GitHub Actions) roda o lint (`ruff` + `black`) e toda a suíte em cada push.
