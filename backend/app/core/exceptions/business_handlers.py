from typing import Optional
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
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

def handle_business_logic_error(request: Request, exc: Exception, message: Optional[str] = None, show_diag: bool = True, logging: bool = True):
    """비즈니스 로직 오류 처리"""
    error_location = get_error_location()
    if logging:
        log_error_with_location("BusinessLogicError", request, exc, error_location)
    
    details = add_location_to_details(str(exc), error_location, show_diag)
    error_detail = create_error_response(
        error_type=ErrorType.BUSINESS_LOGIC_ERROR,
        message=message or "비즈니스 로직 오류가 발생했습니다.",
        details=details,
        severity=ErrorSeverity.MEDIUM,
        category=ErrorCategory.BUSINESS
    )
    
    return JSONResponse(
        status_code=400,
        content=error_detail
    )

def handle_constraint_error(request: Request, exc: Exception, constraint_name: Optional[str] = None, show_diag: bool = True, logging: bool = True):
    """제약 조건 오류 처리"""
    error_location = get_error_location()
    if logging:
        log_error_with_location("ConstraintError", request, exc, error_location)
        if constraint_name:
            dprint(f"Constraint: {constraint_name}")
    
    message = f"제약 조건 '{constraint_name}' 위반" if constraint_name else "제약 조건 위반"
    details = add_location_to_details(str(exc), error_location, show_diag)
    
    error_detail = create_error_response(
        error_type=ErrorType.CONSTRAINT_ERROR,
        message=message,
        details=details,
        severity=ErrorSeverity.HIGH,
        category=ErrorCategory.BUSINESS
    )
    
    return JSONResponse(
        status_code=400,
        content=error_detail
    )

def handle_state_error(request: Request, exc: Exception, current_state: Optional[str] = None, required_state: Optional[str] = None, show_diag: bool = True, logging: bool = True):
    """상태 오류 처리"""
    error_location = get_error_location()
    if logging:
        log_error_with_location("StateError", request, exc, error_location)
        dprint(f"Current State: {current_state}, Required State: {required_state}")
    
    if current_state and required_state:
        message = f"현재 상태 '{current_state}'에서 요구되는 상태 '{required_state}'로 변경할 수 없습니다."
    else:
        message = "상태 변경 오류가 발생했습니다."
    
    details = {
        "current_state": current_state,
        "required_state": required_state,
        "error": str(exc) if show_diag else None
    }
    if error_location and show_diag:
        details["location"] = format_error_location(error_location)
    
    error_detail = create_error_response(
        error_type=ErrorType.STATE_ERROR,
        message=message,
        details=details,
        severity=ErrorSeverity.MEDIUM,
        category=ErrorCategory.BUSINESS
    )
    
    return JSONResponse(
        status_code=400,
        content=error_detail
    )

def handle_not_found_error(request: Request, resource_type: str, resource_id: Optional[str]  = None, show_diag: bool = True, logging: bool = True):
    """리소스 찾을 수 없음 오류 처리"""
    error_location = get_error_location()
    if logging:
        dprint(f"=== NotFoundError ===")
        dprint(f"Request: {request.method} {request.url}")
        if error_location:
            dprint(f"Location: {format_error_location(error_location)}")
        dprint(f"Resource: {resource_type} - {resource_id}")
    
    if resource_id:
        message = f"{resource_type} '{resource_id}'을(를) 찾을 수 없습니다."
    else:
        message = f"{resource_type}을(를) 찾을 수 없습니다."
    
    details = {
        "resource_type": resource_type,
        "resource_id": resource_id
    }
    if error_location and show_diag:
        details["location"] = format_error_location(error_location)
    
    error_detail = create_error_response(
        error_type=ErrorType.BUSINESS_LOGIC_ERROR,
        message=message,
        details=details,
        severity=ErrorSeverity.MEDIUM,
        category=ErrorCategory.BUSINESS
    )
    
    return JSONResponse(
        status_code=404,
        content=error_detail
    )

def handle_duplicate_error(request: Request, resource_type: str, field_name: Optional[str] = None, field_value: Optional[str] = None, show_diag: bool = True, logging: bool = True):
    """중복 오류 처리"""
    error_location = get_error_location()
    if logging:
        dprint(f"=== DuplicateError ===")
        dprint(f"Request: {request.method} {request.url}")
        if error_location:
            dprint(f"Location: {format_error_location(error_location)}")
        dprint(f"Resource: {resource_type} - {field_name}: {field_value}")
    
    if field_name and field_value:
        message = f"{resource_type}의 '{field_name}' 값 '{field_value}'이(가) 이미 존재합니다."
    else:
        message = f"{resource_type}이(가) 이미 존재합니다."
    
    details = {
        "resource_type": resource_type,
        "field_name": field_name,
        "field_value": field_value
    }
    if error_location and show_diag:
        details["location"] = format_error_location(error_location)
    
    error_detail = create_error_response(
        error_type=ErrorType.CONSTRAINT_ERROR,
        message=message,
        details=details,
        severity=ErrorSeverity.MEDIUM,
        category=ErrorCategory.BUSINESS
    )
    
    return JSONResponse(
        status_code=409,
        content=error_detail
    )