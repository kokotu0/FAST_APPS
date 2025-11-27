from fastapi import Request
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from fastapi.exceptions import RequestValidationError, ResponseValidationError
import logging
logger = logging.getLogger(__name__)

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

def handle_validation_error(request: Request, exc: ValidationError, show_diag: bool = True, logging: bool = True):
    """Pydantic 검증 오류 처리"""
    error_location = get_error_location()
    if logging:
        log_error_with_location("ValidationError", request, exc, error_location)
    
    # 검증 오류를 사용자 친화적인 메시지로 변환
    error_messages = []
    for error in exc.errors():
        field = error.get('loc', [])[-1] if error.get('loc') else 'unknown'
        error_type = error.get('type', '')
        msg = error.get('msg', '')
        
        # 에러 타입별 메시지 변환
        if error_type == 'value_error.missing':
            error_messages.append(f"'{field}' 필드는 필수입니다.")
        elif error_type == 'value_error.any_str.min_length':
            error_messages.append(f"'{field}' 필드는 최소 {error.get('ctx', {}).get('limit_value', 0)}자 이상이어야 합니다.")
        elif error_type == 'value_error.any_str.max_length':
            error_messages.append(f"'{field}' 필드는 최대 {error.get('ctx', {}).get('limit_value', 0)}자까지 가능합니다.")
        elif error_type == 'value_error.number.not_gt':
            error_messages.append(f"'{field}' 필드는 {error.get('ctx', {}).get('limit_value', 0)}보다 커야 합니다.")
        elif error_type == 'value_error.number.not_lt':
            error_messages.append(f"'{field}' 필드는 {error.get('ctx', {}).get('limit_value', 0)}보다 작아야 합니다.")
        elif error_type == 'type_error.integer':
            error_messages.append(f"'{field}' 필드는 정수여야 합니다.")
        elif error_type == 'type_error.float':
            error_messages.append(f"'{field}' 필드는 숫자여야 합니다.")
        elif error_type == 'value_error.email':
            error_messages.append(f"'{field}' 필드는 유효한 이메일 형식이어야 합니다.")
        else:
            error_messages.append(f"'{field}': {msg}")
    
    details = {
        "errors": error_messages,
        "raw_errors": exc.errors() if show_diag else None
    }
    
    # 위치 정보 추가
    if error_location and show_diag:
        details["location"] = format_error_location(error_location)
    
    error_detail = create_error_response(
        error_type=ErrorType.VALIDATION_ERROR,
        message="데이터 검증 오류가 발생했습니다.",
        details=details,
        severity=ErrorSeverity.MEDIUM,
        category=ErrorCategory.VALIDATION
    )
    
    return JSONResponse(
        status_code=400,
        content=error_detail
    )

def handle_request_validation_error(request: Request, exc: RequestValidationError, show_diag: bool = True, logging: bool = True):
    """요청 검증 오류 처리"""
    error_location = get_error_location()
    if logging:
        log_error_with_location("RequestValidationError", request, exc, error_location)
        logger.error(f"Error Details: {exc.errors()}")
    
    # 요청 검증 오류를 사용자 친화적인 메시지로 변환
    error_messages = []
    for error in exc.errors():
        location = error.get('loc', [])
        if location:
            if location[0] == 'body':
                field = location[-1] if len(location) > 1 else 'body'
            elif location[0] == 'query':
                field = location[-1] if len(location) > 1 else 'query'
            elif location[0] == 'path':
                field = location[-1] if len(location) > 1 else 'path'
            else:
                field = '/'.join(str(x) for x in location)
        else:
            field = 'unknown'
        
        error_type = error.get('type', '')
        msg = error.get('msg', '')
        
        # 에러 타입별 메시지 변환
        if error_type == 'value_error.missing':
            error_messages.append(f"'{field}' 필드는 필수입니다.")
        elif error_type == 'type_error.integer':
            error_messages.append(f"'{field}' 필드는 정수여야 합니다.")
        elif error_type == 'type_error.float':
            error_messages.append(f"'{field}' 필드는 숫자여야 합니다.")
        elif error_type == 'value_error.any_str.min_length':
            error_messages.append(f"'{field}' 필드는 최소 {error.get('ctx', {}).get('limit_value', 0)}자 이상이어야 합니다.")
        elif error_type == 'value_error.any_str.max_length':
            error_messages.append(f"'{field}' 필드는 최대 {error.get('ctx', {}).get('limit_value', 0)}자까지 가능합니다.")
        else:
            error_messages.append(f"'{field}': {msg}")
    
    details = {
        "errors": error_messages,
        "raw_errors": exc.errors() if show_diag else None,
        "body": exc.body if show_diag else None
    }
    
    # 위치 정보 추가
    if error_location and show_diag:
        details["location"] = format_error_location(error_location)
    
    error_detail = create_error_response(
        error_type=ErrorType.REQUEST_VALIDATION_ERROR,
        message="요청 데이터 검증 오류가 발생했습니다.",
        details=details,
        severity=ErrorSeverity.MEDIUM,
        category=ErrorCategory.VALIDATION
    )
    
    return JSONResponse(
        status_code=422,
        content=error_detail
    )

def handle_response_validation_error(request: Request, exc: ResponseValidationError, show_diag: bool = True, logging: bool = True):
    """응답 검증 오류 처리"""
    error_location = get_error_location()
    if logging:
        log_error_with_location("ResponseValidationError", request, exc, error_location)
        logger.error(f"Error Details: {exc.errors()}")
    
    # 응답 검증 오류를 사용자 친화적인 메시지로 변환
    error_messages = []
    for error in exc.errors():
        location = error.get('loc', [])
        if location:
            if location[0] == 'response':
                field = location[-1] if len(location) > 1 else 'response'
            else:
                field = '/'.join(str(x) for x in location)
        else:
            field = 'unknown'
        
        error_type = error.get('type', '')
        msg = error.get('msg', '')
        
        # 에러 타입별 메시지 변환
        if error_type == 'value_error.missing':
            error_messages.append(f"응답에서 '{field}' 필드가 누락되었습니다.")
        elif error_type == 'type_error.integer':
            error_messages.append(f"응답의 '{field}' 필드는 정수여야 합니다.")
        elif error_type == 'type_error.float':
            error_messages.append(f"응답의 '{field}' 필드는 숫자여야 합니다.")
        elif error_type == 'value_error.any_str.min_length':
            error_messages.append(f"응답의 '{field}' 필드는 최소 {error.get('ctx', {}).get('limit_value', 0)}자 이상이어야 합니다.")
        elif error_type == 'value_error.any_str.max_length':
            error_messages.append(f"응답의 '{field}' 필드는 최대 {error.get('ctx', {}).get('limit_value', 0)}자까지 가능합니다.")
        else:
            error_messages.append(f"응답의 '{field}': {msg}")
    
    details = {
        "errors": error_messages,
        "raw_errors": exc.errors() if show_diag else None
    }
    
    # 위치 정보 추가
    if error_location and show_diag:
        details["location"] = format_error_location(error_location)
    
    error_detail = create_error_response(
        error_type=ErrorType.RESPONSE_VALIDATION_ERROR,
        message="서버 응답 검증 오류가 발생했습니다.",
        details=details,
        severity=ErrorSeverity.MEDIUM,
        category=ErrorCategory.VALIDATION
    )
    
    return JSONResponse(
        status_code=500,
        content=error_detail
    )

def handle_field_validation_error(request: Request, field_name: str, error_message: str, show_diag: bool = True, logging: bool = True):
    """필드별 검증 오류 처리"""
    error_location = get_error_location()
    if logging:
        dprint(f"=== FieldValidationError ===")
        dprint(f"Request: {request.method} {request.url}")
        if error_location:
            dprint(f"Location: {format_error_location(error_location)}")
        dprint(f"Field: {field_name} - {error_message}")
    
    details = {
        "field": field_name,
        "message": error_message
    }
    
    # 위치 정보 추가
    if error_location and show_diag:
        details["location"] = format_error_location(error_location)
    
    error_detail = create_error_response(
        error_type=ErrorType.FIELD_VALIDATION_ERROR,
        message=f"'{field_name}' 필드 검증 오류가 발생했습니다.",
        details=details,
        severity=ErrorSeverity.LOW,
        category=ErrorCategory.VALIDATION
    )
    
    return JSONResponse(
        status_code=400,
        content=error_detail
    ) 