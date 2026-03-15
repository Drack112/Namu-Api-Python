import json
import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

SYSTEM_MESSAGE = """\
Você é um especialista certificado em bem-estar integrado, com formação em saúde física, \
mental e nutrição. Sua missão é criar recomendações de atividades de bem-estar altamente \
personalizadas com base no perfil do usuário.

PRINCÍPIOS OBRIGATÓRIOS:
- Adapte SEMPRE a intensidade e o tipo de atividade ao nível de experiência do usuário.
- Respeite RIGOROSAMENTE qualquer restrição de saúde ou condição especial informada.
- Priorize a segurança: em caso de dúvida, recomende sempre a opção mais conservadora.
- Para condições médicas (gravidez, artrite, hipertensão, etc.), inclua precauções específicas.
- Nunca recomende atividades que possam agravar condições de saúde existentes.

CATEGORIAS DE ATIVIDADES DISPONÍVEIS:
meditação | respiração | yoga | pilates | caminhada | musculação | alongamento |
nutrição | sono | mindfulness | aquática | dança | ciclismo | natação

FORMATO DE RESPOSTA:
Responda EXCLUSIVAMENTE com um objeto JSON válido, sem texto adicional, sem markdown, \
sem explicações fora do JSON. O objeto deve ter exatamente estas chaves:

{
  "activities": [
    {
      "name": "Nome claro e específico da atividade",
      "description": "Como realizar passo a passo, incluindo postura, ritmo e progressão",
      "duration": "Duração recomendada (ex: '20-30 minutos', '3 séries de 10 minutos')",
      "category": "categoria (uma das categorias listadas acima)"
    }
  ],
  "reasoning": "Parágrafo explicando por que essas atividades foram escolhidas para \
este perfil específico, conectando objetivos, restrições e nível de experiência",
  "precautions": [
    "Alerta específico baseado nas restrições ou condições do usuário"
  ]
}

Recomende entre 3 e 5 atividades. Se não houver precauções relevantes, retorne \
"precautions": [].
"""

_FALLBACK_RESPONSE: dict[str, Any] = {
    "activities": [
        {
            "name": "Respiração diafragmática",
            "description": (
                "Sente-se confortavelmente, inspire pelo nariz contando 4 tempos, "
                "segure por 2 tempos e expire pela boca contando 6 tempos."
            ),
            "duration": "10 minutos",
            "category": "respiração",
        }
    ],
    "reasoning": (
        "Não foi possível processar a resposta da IA no momento. "
        "Esta é uma sugestão segura e universal de bem-estar. "
        "Por favor, tente novamente."
    ),
    "precautions": ["Consulte um profissional de saúde para recomendações personalizadas."],
}


def build_user_prompt(user: Any, context: str | None, feedback_context: dict | None = None) -> str:
    goals_text = ", ".join(user.goals) if user.goals else "não informados"
    restrictions_text = user.restrictions or "Nenhuma restrição informada"

    lines = [
        "PERFIL DO USUÁRIO:",
        f"  Nome: {user.name}",
        f"  Idade: {user.age} anos",
        f"  Objetivos de bem-estar: {goals_text}",
        f"  Restrições / Condições especiais: {restrictions_text}",
        f"  Nível de experiência: {user.experience_level}",
    ]

    if context:
        lines += ["", "CONTEXTO ADICIONAL DO DIA:", f"  {context}"]

    if feedback_context and feedback_context.get("preferred_categories"):
        cats = ", ".join(feedback_context["preferred_categories"])
        avg = feedback_context.get("avg_rating", 0)
        total = feedback_context.get("total_feedbacks", 0)
        lines += [
            "",
            f"PREFERÊNCIAS HISTÓRICAS (baseado em {total} avaliações, média {avg}/5):",
            f"  Categorias mais bem avaliadas pelo usuário: {cats}",
            "  Priorize essas categorias, mas inclua variedade quando relevante.",
        ]

    lines += [
        "",
        "Com base nesse perfil, gere recomendações personalizadas de bem-estar.",
        "Responda APENAS com o JSON no formato especificado, sem nenhum texto adicional.",
    ]

    return "\n".join(lines)


def parse_llm_response(raw: str) -> dict[str, Any]:
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass

    fence_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", raw)
    if fence_match:
        try:
            return json.loads(fence_match.group(1))
        except json.JSONDecodeError:
            pass

    brace_match = re.search(r"\{[\s\S]*\}", raw)
    if brace_match:
        try:
            return json.loads(brace_match.group(0))
        except json.JSONDecodeError:
            pass

    logger.warning(
        "Failed to parse LLM response — using fallback", extra={"raw_preview": raw[:300]}
    )
    return _FALLBACK_RESPONSE.copy()
