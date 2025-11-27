from typing import List
from app.api.deps import SessionDep
from fastapi import APIRouter
from app.api.formRegister.schemas import (
    FormRegisterRequest,
    FormRegisterResponse,
    ApiResponse,
    PaginatedResponse,
    FormApiResponse,
    FormListResponse,
    BatchResult,
    KeyValuePair,
)

router = APIRouter(prefix="/formRegister", tags=["formRegister"])


# 기본 엔드포인트
@router.post("/register", response_model=FormRegisterResponse)
def register_form(session: SessionDep, request: FormRegisterRequest):
    return request


# 제네릭 직접 사용 (인라인)
@router.get("/single/{form_id}", response_model=ApiResponse[FormRegisterResponse])
def get_form_with_wrapper(form_id: int):
    """제네릭 래퍼로 감싼 단일 응답"""
    return {
        "success": True,
        "message": "폼 조회 성공",
        "data": {"idx": form_id, "title": "테스트", "description": "설명"}
    }


# 페이지네이션 제네릭
@router.get("/list", response_model=FormListResponse)
def get_form_list(page: int = 1, page_size: int = 10):
    """제네릭 페이지네이션 응답"""
    return {
        "items": [],
        "total": 0,
        "page": page,
        "page_size": page_size,
        "has_next": False,
        "has_prev": page > 1
    }

