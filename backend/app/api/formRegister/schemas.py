from typing import Generic, TypeVar, List, Optional
from datetime import datetime
from pydantic import BaseModel
from sqlmodel import SQLModel

from app.models.FormModels import FormTemplate, FormBase, FormPublishTemplate, PublishStatus


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
    # 배포 관련
    publish_status: PublishStatus | None = None
    publish_start_at: datetime | None = None
    publish_end_at: datetime | None = None
    max_responses: int | None = None
    allow_anonymous: bool | None = None
    require_login: bool | None = None


# ============ FormPublish 관련 스키마 ============
class FormPublishResponse(FormPublishTemplate):
    """폼 배포 응답"""
    pass


class FormPublishCreateRequest(BaseModel):
    """폼 배포 생성 요청"""
    receiver: str  # 이메일 또는 전화번호
    receiver_name: str | None = None
    expired_days: int = 30  # 만료일 (일 단위)


class FormPublishUpdateRequest(BaseModel):
    """폼 배포 수정 요청"""
    receiver: str | None = None
    receiver_name: str | None = None
    expired_at: datetime | None = None
    is_submitted: bool | None = None


class FormPublishBatchRequest(BaseModel):
    """폼 배포 일괄 생성 요청"""
    receivers: List[dict]  # [{"receiver": "email", "receiver_name": "name"}, ...]
    expired_days: int = 30


class FormPublishApiResponse(ApiResponse[FormPublishResponse]):
    """FormPublish 단일 응답"""
    pass


class FormPublishListResponse(PaginatedResponse[FormPublishResponse]):
    """FormPublish 목록 응답"""
    pass


# ============ 공개 폼 관련 스키마 ============
class PublicFormResponse(BaseModel):
    """공개 폼 응답 (토큰으로 접근)"""
    title: str
    description: str | None
    JSONSchema: dict
    UISchema: dict
    Theme: str
    receiver_name: str | None
    is_submitted: bool
    expired_at: datetime


class PublicFormSubmitRequest(BaseModel):
    """공개 폼 제출 요청"""
    responseData: dict


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
