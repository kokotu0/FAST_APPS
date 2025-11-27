import sqlalchemy
from fastapi import Request
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
import logging
logger = logging.getLogger(__name__)
def handle_integrity_error(request: Request, exc: sqlalchemy.exc.IntegrityError, show_diag: bool = True, logging: bool = True):
    """데이터베이스 무결성 오류 처리"""
    # 에러 발생 위치 정보 수집
    error_location = get_error_location()
    
    if logging:
        log_error_with_location("Database Integrity Error", request, exc, error_location)
        
    
    # PostgreSQL 무결성 제약 조건 에러 코드별 메시지 매핑 (23xxx)
    pgcode_messages = {
        "23001": "제약 조건 위반 - RESTRICT",
        "23502": "NOT NULL 제약 조건 위반",
        "23503": "외래 키 제약 조건 위반",
        "23505": "고유 제약 조건 위반",
        "23514": "체크 제약 조건 위반",
        "23P01": "제외 제약 조건 위반",
    }
    
    pgcode = exc.orig.pgcode if hasattr(exc, 'orig') else None
    details = exc.orig.diag.message_detail if hasattr(exc, 'orig') and hasattr(exc.orig, 'diag') and show_diag else None
    logger.error(f"pgcode: {pgcode}, details: {details}")
    logger.error(exc.orig)
    # 에러 코드에 따른 메시지 선택
    if pgcode and pgcode in pgcode_messages:
        message = pgcode_messages[pgcode]
    else:
        message = "데이터베이스 무결성 오류가 발생했습니다."
    
    # 에러 응답에 위치 정보 포함
    #details = add_location_to_details(details, error_location, show_diag)
    
    error_detail = create_error_response(
        error_type=ErrorType.INTEGRITY_ERROR,
        message=message,
        details=details,
        code=pgcode,
        severity=ErrorSeverity.HIGH,
        category=ErrorCategory.DATABASE
    )
    
    return JSONResponse(
        status_code=400,
        content=error_detail
    )

def handle_database_error(request: Request, exc: sqlalchemy.exc.DatabaseError, show_diag: bool = True, logging: bool = True):
    """일반 데이터베이스 오류 처리"""
    # 에러 발생 위치 정보 수집
    error_location = get_error_location()
    
    if logging:
        log_error_with_location("Database Error", request, exc, error_location)
    
    # 에러 응답에 위치 정보 포함
    details = str(exc) if show_diag else None
    #details = add_location_to_details(details, error_location, show_diag)
    
    error_detail = create_error_response(
        error_type=ErrorType.DATABASE_ERROR,
        message="데이터베이스 오류가 발생했습니다.",
        details=details,
        severity=ErrorSeverity.HIGH,
        category=ErrorCategory.DATABASE
    )
    
    return JSONResponse(
        status_code=500,
        content=error_detail
    )

def handle_connection_error(request: Request, exc: sqlalchemy.exc.OperationalError, show_diag: bool = True, logging: bool = True):
    """데이터베이스 연결 오류 처리"""
    # 에러 발생 위치 정보 수집
    error_location = get_error_location()
    
    if logging:
        log_error_with_location("Database Connection Error", request, exc, error_location)
    
    # 에러 응답에 위치 정보 포함
    details = str(exc) if show_diag else None
    #details = add_location_to_details(details, error_location, show_diag)
    
    error_detail = create_error_response(
        error_type=ErrorType.CONNECTION_ERROR,
        message="데이터베이스 연결에 실패했습니다.",
        details=details,
        severity=ErrorSeverity.CRITICAL,
        category=ErrorCategory.DATABASE
    )
    
    return JSONResponse(
        status_code=503,
        content=error_detail
    )

def handle_programming_error(request: Request, exc: sqlalchemy.exc.ProgrammingError, show_diag: bool = True, logging: bool = True):
    """데이터베이스 프로그래밍 오류 처리 (테이블/컬럼/인덱스 관련 오류, 42xxx)"""
    # 에러 발생 위치 정보 수집
    error_location = get_error_location()
    
    if logging:
        log_error_with_location("Database Programming Error", request, exc, error_location)
    
    # PostgreSQL 프로그래밍 에러 코드별 메시지 매핑 (42xxx)
    pgcode_messages = {
        "42P01": "테이블이 존재하지 않습니다",
        "42P02": "인덱스가 존재하지 않습니다",
        "42703": "컬럼이 존재하지 않습니다",
        "42883": "함수가 존재하지 않습니다",
        "42P04": "테이블이 이미 존재합니다",
    }
    
    pgcode = exc.orig.pgcode if hasattr(exc, 'orig') else None
    details = exc.orig.diag.message_detail if hasattr(exc, 'orig') and hasattr(exc.orig, 'diag') and show_diag else None
    logger.error(f"pgcode: {pgcode}, details: {details}")
    logger.error(exc.orig)
    
    # 에러 코드에 따른 메시지 선택
    if pgcode and pgcode in pgcode_messages:
        message = pgcode_messages[pgcode]
    else:
        message = "데이터베이스 프로그래밍 오류가 발생했습니다."
    
    error_detail = create_error_response(
        error_type=ErrorType.DATABASE_ERROR,
        message=message,
        details=details,
        code=pgcode,
        severity=ErrorSeverity.HIGH,
        category=ErrorCategory.DATABASE
    )
    
    return JSONResponse(
        status_code=400,
        content=error_detail
    )   