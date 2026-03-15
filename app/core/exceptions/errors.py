class AppError(Exception):
    """Base class for all domain errors."""


class NotFoundError(AppError):
    def __init__(self, resource: str = "Recurso"):
        self.resource = resource
        super().__init__(f"{resource} não encontrado")


class ConflictError(AppError):
    pass


class ExternalServiceError(AppError):
    pass
