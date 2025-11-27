from enum import Enum
from typing import Optional, Any, Dict

class ErrorType(Enum):
    """에러 타입 정의"""
    # 데이터베이스 관련
    INTEGRITY_ERROR = "IntegrityError"
    DATABASE_ERROR = "DatabaseError"
    CONNECTION_ERROR = "ConnectionError"
    
    # 검증 관련
    VALIDATION_ERROR = "ValidationError"
    REQUEST_VALIDATION_ERROR = "RequestValidationError"
    FIELD_VALIDATION_ERROR = "FieldValidationError"
    RESPONSE_VALIDATION_ERROR = "ResponseValidationError"
    
    # 인증/권한 관련
    AUTHENTICATION_ERROR = "AuthenticationError"
    AUTHORIZATION_ERROR = "AuthorizationError"
    TOKEN_ERROR = "TokenError"
    
    # 비즈니스 로직 관련
    BUSINESS_LOGIC_ERROR = "BusinessLogicError"
    CONSTRAINT_ERROR = "ConstraintError"
    STATE_ERROR = "StateError"
    
    # 파일 관련
    FILE_ERROR = "FileError"
    UPLOAD_ERROR = "UploadError"
    DOWNLOAD_ERROR = "DownloadError"
    
    # 외부 API 관련
    EXTERNAL_API_ERROR = "ExternalApiError"
    NETWORK_ERROR = "NetworkError"
    TIMEOUT_ERROR = "TimeoutError"
    
    # 일반 오류
    HTTP_ERROR = "HTTPError"
    SERVER_ERROR = "ServerError"
    UNKNOWN_ERROR = "UnknownError"

class ErrorSeverity(Enum):
    """에러 심각도 정의"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class ErrorCategory(Enum):
    """에러 카테고리 정의"""
    DATABASE = "database"
    VALIDATION = "validation"
    AUTHENTICATION = "authentication"
    BUSINESS = "business"
    FILE = "file"
    EXTERNAL = "external"
    SYSTEM = "system"

def create_error_response(
    error_type: ErrorType,
    message: str,
    details: Optional[Any] = None,
    code: Optional[str] = None,
    severity: ErrorSeverity = ErrorSeverity.MEDIUM,
    category: ErrorCategory = ErrorCategory.SYSTEM
) -> Dict[str, Any]:
    """통일된 에러 응답 생성"""
    return {
        "type": error_type.value,
        "message": message,
        "details": details,
        "code": code,
        "severity": severity.value,
        "category": category.value
    } 