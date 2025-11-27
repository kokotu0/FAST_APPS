from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from jose import JWTError
from .error_types import (
    ErrorType, ErrorSeverity, ErrorCategory, create_error_response
)
from .error_location import (
    get_error_location,
    format_error_location, 
    log_error_with_location,
    add_location_to_details
)
from core.internal.debug import dprint

def handle_authentication_error(request: Request, exc: HTTPException, show_diag: bool = True, logging: bool = True):
    """인증 오류 처리"""
    error_location = get_error_location()
    if logging:
        log_error_with_location("AuthenticationError", request, exc, error_location)
        dprint(f"Status Code: {exc.status_code}")
    
    details = add_location_to_details(str(exc.detail), error_location, show_diag)
    error_detail = create_error_response(
        error_type=ErrorType.AUTHENTICATION_ERROR,
        message="인증이 필요합니다.",
        details=details,
        code=str(exc.status_code),
        severity=ErrorSeverity.HIGH,
        category=ErrorCategory.AUTHENTICATION
    )
    
    return JSONResponse(
        status_code=401,
        content=error_detail
    )

def handle_authorization_error(request: Request, exc: HTTPException, show_diag: bool = True, logging: bool = True):
    """권한 오류 처리"""
    error_location = get_error_location()
    if logging:
        log_error_with_location("AuthorizationError", request, exc, error_location)
        dprint(f"Status Code: {exc.status_code}")
    
    details = add_location_to_details(str(exc.detail), error_location, show_diag)
    error_detail = create_error_response(
        error_type=ErrorType.AUTHORIZATION_ERROR,
        message="접근 권한이 없습니다.",
        details=details,
        code=str(exc.status_code),
        severity=ErrorSeverity.HIGH,
        category=ErrorCategory.AUTHENTICATION
    )
    
    return JSONResponse(
        status_code=403,
        content=error_detail
    )

def handle_token_error(request: Request, exc: JWTError, show_diag: bool = True, logging: bool = True):
    """토큰 오류 처리"""
    error_location = get_error_location()
    if logging:
        log_error_with_location("TokenError", request, exc, error_location)
    
    details = add_location_to_details(str(exc), error_location, show_diag)
    error_detail = create_error_response(
        error_type=ErrorType.TOKEN_ERROR,
        message="유효하지 않은 토큰입니다.",
        details=details,
        severity=ErrorSeverity.HIGH,
        category=ErrorCategory.AUTHENTICATION
    )
    
    return JSONResponse(
        status_code=401,
        content=error_detail
    )

def handle_expired_token_error(request: Request, exc: Exception, show_diag: bool = True, logging: bool = True):
    """만료된 토큰 오류 처리"""
    error_location = get_error_location()
    if logging:
        log_error_with_location("ExpiredTokenError", request, exc, error_location)
    
    details = add_location_to_details(str(exc), error_location, show_diag)
    error_detail = create_error_response(
        error_type=ErrorType.TOKEN_ERROR,
        message="토큰이 만료되었습니다.",
        details=details,
        severity=ErrorSeverity.MEDIUM,
        category=ErrorCategory.AUTHENTICATION
    )
    
    return JSONResponse(
        status_code=401,
        content=error_detail
    )