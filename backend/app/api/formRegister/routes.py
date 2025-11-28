from typing import List
from uuid import uuid4
from app.api.deps import SessionDep, CurrentUser
from fastapi import APIRouter, HTTPException
from sqlmodel import select
from app.api.formRegister.schemas import (
    FormRegisterRequest,
    FormRegisterResponse,
    ApiResponse,
    FormApiResponse,
    FormListResponse,
    FormCreateRequest,
    FormUpdateRequest,
)
from app.models.FormModels import FormTable

router = APIRouter(prefix="/formRegister", tags=["formRegister"])


# 폼 목록 조회 (먼저 정의해야 /{form_uuid}보다 우선)
@router.get("/", response_model=FormListResponse)
def get_form_list(
    session: SessionDep,
    current_user: CurrentUser,
    page: int = 1,
    page_size: int = 10,
):
    """폼 목록 조회"""
    offset = (page - 1) * page_size
    statement = select(FormTable).offset(offset).limit(page_size)
    forms = session.exec(statement).all()
    
    # 전체 개수
    count_statement = select(FormTable)
    total = len(session.exec(count_statement).all())
    
    return {
        "items": forms,
        "total": total,
        "page": page,
        "page_size": page_size,
        "has_next": offset + page_size < total,
        "has_prev": page > 1,
    }


# 폼 생성
@router.post("/", response_model=FormApiResponse)
def create_form(
    session: SessionDep,
    current_user: CurrentUser,
    request: FormCreateRequest,
):
    """폼 생성 (uuid 자동 생성)"""
    form = FormTable(
        uuid=request.uuid or str(uuid4()),
        category=request.category,
        title=request.title,
        description=request.description,
        JSONSchema=request.JSONSchema,
        UISchema=request.UISchema,
        Theme=request.Theme,
    )
    session.add(form)
    session.commit()
    session.refresh(form)
    return {
        "success": True,
        "message": "폼 생성 성공",
        "data": form,
    }


# 폼 상세 조회
@router.get("/{form_uuid}", response_model=FormApiResponse)
def get_form(
    session: SessionDep,
    current_user: CurrentUser,
    form_uuid: str,
):
    """폼 상세 조회"""
    statement = select(FormTable).where(FormTable.uuid == form_uuid)
    form = session.exec(statement).first()
    if not form:
        raise HTTPException(status_code=404, detail="Form not found")
    return {
        "success": True,
        "message": "폼 조회 성공",
        "data": form,
    }


# 폼 수정
@router.put("/{form_uuid}", response_model=FormApiResponse)
def update_form(
    session: SessionDep,
    current_user: CurrentUser,
    form_uuid: str,
    request: FormUpdateRequest,
):
    """폼 수정"""
    statement = select(FormTable).where(FormTable.uuid == form_uuid)
    form = session.exec(statement).first()
    if not form:
        raise HTTPException(status_code=404, detail="Form not found")
    
    update_data = request.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(form, key, value)
    
    session.add(form)
    session.commit()
    session.refresh(form)
    return {
        "success": True,
        "message": "폼 수정 성공",
        "data": form,
    }


# 폼 삭제
@router.delete("/{form_uuid}")
def delete_form(
    session: SessionDep,
    current_user: CurrentUser,
    form_uuid: str,
):
    """폼 삭제"""
    statement = select(FormTable).where(FormTable.uuid == form_uuid)
    form = session.exec(statement).first()
    if not form:
        raise HTTPException(status_code=404, detail="Form not found")
    
    session.delete(form)
    session.commit()
    return {"success": True, "message": "폼 삭제 성공"}
