from typing import List
from uuid import uuid4
from datetime import datetime, timedelta
import secrets
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
    FormPublishResponse,
    FormPublishCreateRequest,
    FormPublishUpdateRequest,
    FormPublishBatchRequest,
    FormPublishApiResponse,
    FormPublishListResponse,
    PublicFormResponse,
    PublicFormSubmitRequest,
)
from app.models.FormModels import FormTable, FormPublishTable

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


# 폼 상세 조회 (uuid 기반)
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


# ============ FormPublish API ============

# 폼 배포 목록 조회 (uuid 기반)
@router.get("/{form_uuid}/publish", response_model=FormPublishListResponse)
def get_form_publishes(
    session: SessionDep,
    current_user: CurrentUser,
    form_uuid: str,
    page: int = 1,
    page_size: int = 10,
):
    """폼 배포 목록 조회"""
    # 폼 확인
    form_statement = select(FormTable).where(FormTable.uuid == form_uuid)
    form = session.exec(form_statement).first()
    if not form:
        raise HTTPException(status_code=404, detail="Form not found")
    
    offset = (page - 1) * page_size
    statement = select(FormPublishTable).where(
        FormPublishTable.form_idx == form.idx
    ).offset(offset).limit(page_size)
    publishes = session.exec(statement).all()
    
    # 전체 개수
    count_statement = select(FormPublishTable).where(
        FormPublishTable.form_idx == form.idx
    )
    total = len(session.exec(count_statement).all())
    
    return {
        "items": publishes,
        "total": total,
        "page": page,
        "page_size": page_size,
        "has_next": offset + page_size < total,
        "has_prev": page > 1,
    }


# 폼 배포 생성 (단일, uuid 기반)
@router.post("/{form_uuid}/publish", response_model=FormPublishApiResponse)
def create_form_publish(
    session: SessionDep,
    current_user: CurrentUser,
    form_uuid: str,
    request: FormPublishCreateRequest,
):
    """폼 배포 생성"""
    # 폼 확인
    form_statement = select(FormTable).where(FormTable.uuid == form_uuid)
    form = session.exec(form_statement).first()
    if not form:
        raise HTTPException(status_code=404, detail="Form not found")
    
    # 토큰 생성
    token = secrets.token_urlsafe(32)
    
    publish = FormPublishTable(
        form_idx=form.idx,
        receiver=request.receiver,
        receiver_name=request.receiver_name,
        token=token,
        expired_at=datetime.now() + timedelta(days=request.expired_days),
    )
    session.add(publish)
    session.commit()
    session.refresh(publish)
    
    return {
        "success": True,
        "message": "배포 생성 성공",
        "data": publish,
    }


# 폼 배포 일괄 생성 (uuid 기반)
@router.post("/{form_uuid}/publish/batch", response_model=ApiResponse)
def create_form_publish_batch(
    session: SessionDep,
    current_user: CurrentUser,
    form_uuid: str,
    request: FormPublishBatchRequest,
):
    """폼 배포 일괄 생성"""
    # 폼 확인
    form_statement = select(FormTable).where(FormTable.uuid == form_uuid)
    form = session.exec(form_statement).first()
    if not form:
        raise HTTPException(status_code=404, detail="Form not found")
    
    created_count = 0
    for receiver_info in request.receivers:
        token = secrets.token_urlsafe(32)
        publish = FormPublishTable(
            form_idx=form.idx,
            receiver=receiver_info.get("receiver", ""),
            receiver_name=receiver_info.get("receiver_name"),
            token=token,
            expired_at=datetime.now() + timedelta(days=request.expired_days),
        )
        session.add(publish)
        created_count += 1
    
    session.commit()
    
    return {
        "success": True,
        "message": f"{created_count}개 배포 생성 성공",
        "data": {"created_count": created_count},
    }


# 폼 배포 수정
@router.put("/{form_uuid}/publish/{publish_idx}", response_model=FormPublishApiResponse)
def update_form_publish(
    session: SessionDep,
    current_user: CurrentUser,
    form_uuid: str,
    publish_idx: int,
    request: FormPublishUpdateRequest,
):
    """폼 배포 수정"""
    statement = select(FormPublishTable).where(FormPublishTable.idx == publish_idx)
    publish = session.exec(statement).first()
    if not publish:
        raise HTTPException(status_code=404, detail="Publish not found")
    
    update_data = request.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(publish, key, value)
    
    session.add(publish)
    session.commit()
    session.refresh(publish)
    
    return {
        "success": True,
        "message": "배포 수정 성공",
        "data": publish,
    }


# 폼 배포 삭제
@router.delete("/{form_uuid}/publish/{publish_idx}")
def delete_form_publish(
    session: SessionDep,
    current_user: CurrentUser,
    form_uuid: str,
    publish_idx: int,
):
    """폼 배포 삭제"""
    statement = select(FormPublishTable).where(FormPublishTable.idx == publish_idx)
    publish = session.exec(statement).first()
    if not publish:
        raise HTTPException(status_code=404, detail="Publish not found")
    
    session.delete(publish)
    session.commit()
    
    return {"success": True, "message": "배포 삭제 성공"}


# ============ 통계 API ============

# 폼 응답 통계 조회
@router.get("/{form_uuid}/stats")
def get_form_stats(
    session: SessionDep,
    current_user: CurrentUser,
    form_uuid: str,
):
    """폼 응답 통계 조회 (배포 현황 + 질문별 응답 집계)"""
    # 폼 확인
    form_statement = select(FormTable).where(FormTable.uuid == form_uuid)
    form = session.exec(form_statement).first()
    if not form:
        raise HTTPException(status_code=404, detail="Form not found")
    
    # 배포 목록 전체 조회
    publish_statement = select(FormPublishTable).where(
        FormPublishTable.form_idx == form.idx
    )
    publishes = session.exec(publish_statement).all()
    
    # 배포 현황 통계
    total_count = len(publishes)
    submitted_count = sum(1 for p in publishes if p.is_submitted)
    pending_count = total_count - submitted_count
    expired_count = sum(1 for p in publishes if not p.is_submitted and p.expired_at < datetime.now())
    email_sent_count = sum(1 for p in publishes if p.is_email_sent)
    email_not_sent_count = total_count - email_sent_count
    
    # 질문별 응답 집계
    field_stats = {}
    schema_properties = form.JSONSchema.get("properties", {})
    
    for field_key, field_schema in schema_properties.items():
        field_title = field_schema.get("title", field_key)
        field_type = field_schema.get("type", "string")
        
        # 해당 필드에 대한 응답 집계
        responses = []
        for publish in publishes:
            if publish.is_submitted and publish.responseSchema:
                value = publish.responseSchema.get(field_key)
                if value is not None:
                    responses.append(value)
        
        # 타입별 집계
        if field_type in ["string", "number", "integer"]:
            # enum이 있는 경우 (선택형 질문)
            if "enum" in field_schema:
                value_counts = {}
                for resp in responses:
                    value_counts[str(resp)] = value_counts.get(str(resp), 0) + 1
                field_stats[field_key] = {
                    "title": field_title,
                    "type": field_type,
                    "is_enum": True,
                    "total_responses": len(responses),
                    "value_counts": value_counts,
                }
            else:
                # 자유 입력 질문
                field_stats[field_key] = {
                    "title": field_title,
                    "type": field_type,
                    "is_enum": False,
                    "total_responses": len(responses),
                    "responses": responses[:100],  # 최대 100개까지만
                }
        elif field_type == "boolean":
            true_count = sum(1 for r in responses if r is True)
            false_count = sum(1 for r in responses if r is False)
            field_stats[field_key] = {
                "title": field_title,
                "type": field_type,
                "is_enum": True,
                "total_responses": len(responses),
                "value_counts": {"true": true_count, "false": false_count},
            }
        elif field_type == "array":
            # 복수 선택 질문
            value_counts = {}
            for resp in responses:
                if isinstance(resp, list):
                    for item in resp:
                        value_counts[str(item)] = value_counts.get(str(item), 0) + 1
            field_stats[field_key] = {
                "title": field_title,
                "type": field_type,
                "is_enum": True,
                "total_responses": len(responses),
                "value_counts": value_counts,
            }
    
    return {
        "success": True,
        "message": "통계 조회 성공",
        "data": {
            "form_uuid": form_uuid,
            "form_title": form.title,
            "publish_stats": {
                "total": total_count,
                "submitted": submitted_count,
                "pending": pending_count,
                "expired": expired_count,
                "email_sent": email_sent_count,
                "email_not_sent": email_not_sent_count,
                "submission_rate": round(submitted_count / total_count * 100, 1) if total_count > 0 else 0,
            },
            "field_stats": field_stats,
        },
    }


# 이메일 전송 상태 업데이트
@router.put("/{form_uuid}/publish/{publish_idx}/email-sent")
def update_email_sent_status(
    session: SessionDep,
    current_user: CurrentUser,
    form_uuid: str,
    publish_idx: int,
):
    """이메일 전송 상태 업데이트"""
    statement = select(FormPublishTable).where(FormPublishTable.idx == publish_idx)
    publish = session.exec(statement).first()
    if not publish:
        raise HTTPException(status_code=404, detail="Publish not found")
    
    publish.is_email_sent = True
    publish.email_sent_at = datetime.now()
    publish.email_sent_count = (publish.email_sent_count or 0) + 1
    
    session.add(publish)
    session.commit()
    session.refresh(publish)
    
    return {
        "success": True,
        "message": "이메일 전송 상태 업데이트 성공",
        "data": publish,
    }


# ============ 공개 폼 API (인증 불필요) ============

# 공개 폼 조회 (토큰)
@router.get("/public/{token}", response_model=ApiResponse[PublicFormResponse])
def get_public_form(
    session: SessionDep,
    token: str,
):
    """공개 폼 조회 (토큰으로 접근, 로그인 불필요)"""
    # 배포 정보 조회
    statement = select(FormPublishTable).where(FormPublishTable.token == token)
    publish = session.exec(statement).first()
    if not publish:
        raise HTTPException(status_code=404, detail="유효하지 않은 링크입니다")
    
    # 만료 확인
    if publish.expired_at < datetime.now():
        raise HTTPException(status_code=410, detail="링크가 만료되었습니다")
    
    # 폼 조회
    form_statement = select(FormTable).where(FormTable.idx == publish.form_idx)
    form = session.exec(form_statement).first()
    if not form:
        raise HTTPException(status_code=404, detail="폼을 찾을 수 없습니다")
    
    return {
        "success": True,
        "message": "폼 조회 성공",
        "data": {
            "title": form.title,
            "description": form.description,
            "JSONSchema": form.JSONSchema,
            "UISchema": form.UISchema,
            "Theme": form.Theme,
            "receiver_name": publish.receiver_name,
            "is_submitted": publish.is_submitted,
            "expired_at": publish.expired_at,
        },
    }


# 공개 폼 제출 (만료 전까지 수정 가능)
@router.post("/public/{token}/submit")
def submit_public_form(
    session: SessionDep,
    token: str,
    request: PublicFormSubmitRequest,
):
    """공개 폼 제출 (만료 전까지 수정 가능)"""
    # 배포 정보 조회
    statement = select(FormPublishTable).where(FormPublishTable.token == token)
    publish = session.exec(statement).first()
    if not publish:
        raise HTTPException(status_code=404, detail="유효하지 않은 링크입니다")
    
    # 만료 확인
    if publish.expired_at < datetime.now():
        raise HTTPException(status_code=410, detail="링크가 만료되었습니다")
    
    # 제출/수정 처리 (만료 전까지 수정 가능)
    is_update = publish.is_submitted
    publish.responseSchema = request.responseData
    publish.is_submitted = True
    publish.submitted_at = datetime.now()
    
    session.add(publish)
    session.commit()
    
    return {
        "success": True, 
        "message": "수정 완료" if is_update else "제출 완료"
    }
