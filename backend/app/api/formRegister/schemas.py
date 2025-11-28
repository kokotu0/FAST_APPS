from typing import Generic, TypeVar, List, Optional
from pydantic import BaseModel
from sqlmodel import SQLModel

from app.models.FormModels import FormTemplate, FormBase


# ============ 제네릭 타입 변수 ============
T = TypeVar("T")
DataT = TypeVar("DataT", bound=BaseModel)


# ============ 제네릭 응답 래퍼 ============
class ApiResponse(SQLModel, Generic[T]):
    """제네릭 API 응답 래퍼"""
    success: bool = True
    message: str = "OK"
    data: T | None = None


class PaginatedResponse(SQLModel, Generic[T]):
    """제네릭 페이지네이션 응답"""
    items: List[T]
    total: int
    page: int = 1
    page_size: int = 10
    has_next: bool = False
    has_prev: bool = False


class ErrorResponse(SQLModel):
    """에러 응답"""
    success: bool = False
    message: str
    error_code: str | None = None
    details: dict | None = None


# ============ Form 관련 스키마 ============
class FormRegisterRequest(FormBase):
    pass


class FormRegisterResponse(FormTemplate):
    pass


class FormCreateRequest(BaseModel):
    """폼 생성 요청"""
    uuid: str | None = None  # None이면 서버에서 자동 생성
    category: str = "default"
    title: str
    description: str | None = None
    JSONSchema: dict = {}
    UISchema: dict = {}
    Theme: str = "mui"


class FormUpdateRequest(BaseModel):
    """폼 수정 요청"""
    category: str | None = None
    title: str | None = None
    description: str | None = None
    JSONSchema: dict | None = None
    UISchema: dict | None = None
    Theme: str | None = None
    useYN: bool | None = None


# ============ 제네릭 사용 예시 ============
class FormApiResponse(ApiResponse[FormRegisterResponse]):
    """Form 단일 응답 (제네릭 구체화)"""
    pass


class FormListResponse(PaginatedResponse[FormRegisterResponse]):
    """Form 목록 응답 (제네릭 구체화)"""
    pass


# ============ 다중 제네릭 예시 ============
K = TypeVar("K")
V = TypeVar("V")

class KeyValuePair(SQLModel, Generic[K, V]):
    """키-값 쌍 제네릭"""
    key: K
    value: V


class BatchResult(SQLModel, Generic[T]):
    """배치 처리 결과"""
    succeeded: List[T]
    failed: List[T]
    total_count: int
    success_count: int
    fail_count: int
