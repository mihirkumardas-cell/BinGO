"""
CleanTrack AI — Custom HTTP Exception Handlers
"""
from fastapi import Request
from fastapi.responses import JSONResponse


class CleanTrackException(Exception):
    """Base exception for domain errors."""
    def __init__(self, message: str, status_code: int = 400):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class NotFoundException(CleanTrackException):
    def __init__(self, resource: str, id: str):
        super().__init__(f"{resource} with id '{id}' not found", status_code=404)


class DuplicateReportException(CleanTrackException):
    def __init__(self, original_id: str):
        super().__init__(
            f"A similar report already exists nearby (id: {original_id})",
            status_code=409,
        )


class StorageException(CleanTrackException):
    def __init__(self, detail: str):
        super().__init__(f"Storage error: {detail}", status_code=500)


class AIServiceException(CleanTrackException):
    def __init__(self, detail: str):
        super().__init__(f"AI service error: {detail}", status_code=502)


async def cleantrack_exception_handler(request: Request, exc: CleanTrackException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.message, "type": type(exc).__name__},
    )


async def generic_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"detail": "An internal error occurred", "type": "InternalServerError"},
    )
