from typing import Optional
from functools import wraps
import pprint
from typing import Callable
from fastapi import HTTPException, Request, Response
from fastapi.responses import JSONResponse
import sqlalchemy
from starlette.middleware.base import BaseHTTPMiddleware
from pydantic import ValidationError
from fastapi.exceptions import RequestValidationError, ResponseValidationError
from jose import JWTError
from core.internal.debug import dprint
import traceback
from .error_location import (
    get_error_location,
    format_error_location,
    log_error_with_location,
    add_location_to_details,
)
import logging
logger = logging.getLogger(__name__)
# 에러 타입 및 핸들러 import
from .error_types import ErrorType, ErrorSeverity, ErrorCategory, create_error_response
from .database_handlers import (
    handle_integrity_error,
    handle_database_error,
    handle_connection_error,
    handle_programming_error,
)
from .validation_handlers import (
    handle_response_validation_error,
    handle_validation_error,
    handle_request_validation_error,
    handle_field_validation_error,
)
from .auth_handlers import (
    handle_authentication_error,
    handle_authorization_error,
    handle_token_error,
    handle_expired_token_error,
)
from .business_handlers import (
    handle_business_logic_error,
    handle_constraint_error,
    handle_state_error,
    handle_not_found_error,
    handle_duplicate_error,
)


def handle_error(showDiag: bool = True, logging: bool = True):
    """기존 데코레이터 (호환성 유지용)"""

    def f(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)

            except sqlalchemy.exc.IntegrityError as e:
                error_location = get_error_location()
                if logging:
                    dprint(f"=== IntegrityError in decorator ===")
                    if error_location:
                        dprint(f"Location: {format_error_location(error_location)}")
                    dprint(f"Message: {str(e)}")
                    if hasattr(e, "orig"):
                        dprint(f"pgcode: {e.orig.pgcode}")
                        if hasattr(e.orig, "diag"):
                            dprint(f"detail: {e.orig.diag.message_detail}")
                details = (
                    e.orig.diag.message_detail
                    if hasattr(e, "orig") and hasattr(e.orig, "diag")
                    else str(e)
                )
                details = add_location_to_details(details, error_location, showDiag)

                error_detail = create_error_response(
                    error_type=ErrorType.INTEGRITY_ERROR,
                    message="데이터베이스 무결성 오류가 발생했습니다.",
                    details=details,
                    code=e.orig.pgcode if hasattr(e, "orig") else None,
                    severity=ErrorSeverity.HIGH,
                    category=ErrorCategory.DATABASE,
                )
                raise HTTPException(status_code=400, detail=error_detail)

            except Exception as e:
                error_location = get_error_location()
                if logging:
                    dprint(f"=== Unknown Error in decorator ===")
                    if error_location:
                        dprint(f"Location: {format_error_location(error_location)}")
                    dprint(f"Error: {str(e)}")

                details = add_location_to_details(str(e), error_location, showDiag)
                error_detail = create_error_response(
                    error_type=ErrorType.UNKNOWN_ERROR,
                    message="서버 내부 오류가 발생했습니다.",
                    details=details,
                    severity=ErrorSeverity.HIGH,
                    category=ErrorCategory.SYSTEM,
                )
                raise HTTPException(status_code=500, detail=error_detail)

        return wrapper

    return f


def create_exception_handlers(app, show_diag: bool = True, logging: bool = True):
    """FastAPI 앱에 예외 핸들러들을 추가하는 함수"""

    @app.exception_handler(sqlalchemy.exc.IntegrityError)
    async def integrity_error_handler(
        request: Request, exc: sqlalchemy.exc.IntegrityError
    ):
        return handle_integrity_error(request, exc, show_diag, logging)

    @app.exception_handler(sqlalchemy.exc.DatabaseError)
    async def database_error_handler(
        request: Request, exc: sqlalchemy.exc.DatabaseError
    ):
        return handle_database_error(request, exc, show_diag, logging)

    @app.exception_handler(sqlalchemy.exc.OperationalError)
    async def connection_error_handler(
        request: Request, exc: sqlalchemy.exc.OperationalError
    ):
        return handle_connection_error(request, exc, show_diag, logging)

    @app.exception_handler(sqlalchemy.exc.ProgrammingError)
    async def programming_error_handler(
        request: Request, exc: sqlalchemy.exc.ProgrammingError
    ):
        return handle_programming_error(request, exc, show_diag, logging)

    @app.exception_handler(ValidationError)
    async def validation_error_handler(request: Request, exc: ValidationError):
        return handle_validation_error(request, exc, show_diag, logging)

    @app.exception_handler(RequestValidationError)
    async def request_validation_error_handler(
        request: Request, exc: RequestValidationError
    ):
        return handle_request_validation_error(request, exc, show_diag, logging)
    
    @app.exception_handler(ResponseValidationError)
    async def response_validation_error_handler(
        request: Request, exc: ResponseValidationError
    ):
        return handle_response_validation_error(request, exc, show_diag, logging)
    
    @app.exception_handler(JWTError)
    async def jwt_error_handler(request: Request, exc: JWTError):
        return handle_token_error(request, exc, show_diag, logging)

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        error_location = get_error_location()
        logger.error(f"Unexpected {type(exc).__name__}: {str(exc)}")

        details = add_location_to_details(str(exc), error_location, show_diag)
        error_detail = create_error_response(
            error_type=ErrorType.UNKNOWN_ERROR,
            message="서버 내부 오류가 발생했습니다.",
            details=details,
            severity=ErrorSeverity.HIGH,
            category=ErrorCategory.SYSTEM,
        )
        # CORS 헤더를 직접 추가한 응답 반환 -> 왠지는 모르겠지만 다른 핸들러는 이거 없어도 잘 돌아감.
        return JSONResponse(
            status_code=500,
            content=error_detail,
            headers={
                "Access-Control-Allow-Origin": request.headers.get("origin", "*"),
                "Access-Control-Allow-Credentials": "true",
            }
        )

# 기존 미들웨어는 호환성을 위해 유지하되 사용하지 않음
class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """전역 에러 처리 미들웨어 (호환성 유지용)"""

    def __init__(self, app, show_diag: bool = True, logging: bool = True):
        super().__init__(app)
        self.show_diag = show_diag
        self.logging = logging

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        try:
            return await call_next(request)
        except Exception as e:
            # 미들웨어에서는 단순히 로깅만 하고 예외를 다시 발생시킴
            if self.logging:
                dprint(f"Middleware caught error: {str(e)}")
            raise e
