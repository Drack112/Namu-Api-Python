import logging
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

logger = logging.getLogger(__name__)

_PT_BR: dict[str, str] = {
    "missing": "O campo '{field}' é obrigatório.",
    "string_too_short": "O campo '{field}' deve ter no mínimo {min_length} caractere(s).",
    "string_too_long": "O campo '{field}' deve ter no máximo {max_length} caractere(s).",
    "string_type": "O campo '{field}' deve ser um texto.",
    "string_pattern_mismatch": "O campo '{field}' não corresponde ao padrão esperado.",
    "int_parsing": "O campo '{field}' deve ser um número inteiro.",
    "int_type": "O campo '{field}' deve ser um número inteiro.",
    "float_parsing": "O campo '{field}' deve ser um número.",
    "float_type": "O campo '{field}' deve ser um número.",
    "bool_parsing": "O campo '{field}' deve ser verdadeiro ou falso.",
    "bool_type": "O campo '{field}' deve ser verdadeiro ou falso.",
    "greater_than_equal": "O campo '{field}' deve ser maior ou igual a {ge}.",
    "less_than_equal": "O campo '{field}' deve ser menor ou igual a {le}.",
    "greater_than": "O campo '{field}' deve ser maior que {gt}.",
    "less_than": "O campo '{field}' deve ser menor que {lt}.",
    "literal_error": "O campo '{field}' deve ser um dos valores: {expected}.",
    "enum": "O campo '{field}' deve ser um dos valores permitidos.",
    "list_too_short": "O campo '{field}' deve ter no mínimo {min_length} item(ns).",
    "list_too_long": "O campo '{field}' deve ter no máximo {max_length} item(ns).",
    "url_parsing": "O campo '{field}' deve ser uma URL válida.",
    "value_error": "Valor inválido para o campo '{field}'.",
    "json_invalid": "O corpo da requisição contém JSON inválido.",
}


def _translate_error(error: dict) -> dict[str, Any]:
    error_type = error.get("type", "")
    loc = error.get("loc", [])
    field = ".".join(str(p) for p in loc if p not in ("body", "query", "path"))
    ctx = error.get("ctx", {})

    template = _PT_BR.get(error_type)
    if template:
        try:
            message = template.format(field=field, **ctx)
        except KeyError:
            message = template.format(field=field)
    else:
        message = f"Erro no campo '{field}': {error.get('msg', error_type)}"

    return {"field": field or None, "message": message}


def _error_body(status_code: int, message: str, path: str, details: Any = None) -> dict:
    body: dict = {"status_code": status_code, "path": path, "message": message}
    if details is not None:
        body["details"] = details
    return body


async def _validation_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    details = [_translate_error(e) for e in exc.errors()]
    return JSONResponse(
        status_code=422,
        content=_error_body(
            422,
            "Erro de validação nos dados enviados.",
            request.url.path,
            details,
        ),
    )


async def _http_handler(request: Request, exc: HTTPException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content=_error_body(exc.status_code, exc.detail, request.url.path),
    )


async def _sqlalchemy_handler(request: Request, exc: SQLAlchemyError) -> JSONResponse:
    logger.error(
        "Erro no banco de dados",
        extra={"path": request.url.path, "error": str(exc)},
        exc_info=True,
    )
    return JSONResponse(
        status_code=500,
        content=_error_body(500, "Erro interno", request.url.path),
    )


async def _unhandled_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error(
        "Erro inesperado",
        extra={"path": request.url.path, "error": str(exc)},
        exc_info=True,
    )
    return JSONResponse(
        status_code=500,
        content=_error_body(500, "Erro interno do servidor.", request.url.path),
    )


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(RequestValidationError, _validation_handler)
    app.add_exception_handler(HTTPException, _http_handler)
    app.add_exception_handler(SQLAlchemyError, _sqlalchemy_handler)
    app.add_exception_handler(Exception, _unhandled_handler)
