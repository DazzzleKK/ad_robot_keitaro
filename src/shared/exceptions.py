class AppError(Exception):
    code = "internal_error"

    def __init__(self, message: str, *, cause: BaseException | None = None) -> None:
        super().__init__(message)
        self.message = message
        if cause is not None:
            self.__cause__ = cause


class DomainError(AppError):
    code = "domain_error"


class InfraError(AppError):
    code = "infra_error"
