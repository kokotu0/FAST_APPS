import datetime
from uuid import UUID, uuid4
from sqlmodel import JSON, Column, Field, SQLModel, Relationship
from typing import Any, Dict, List, Optional
from enum import Enum

from app.core.model import Base


class PublishStatus(str, Enum):
    """배포 상태"""
    DRAFT = "draft"           # 초안 (미배포)
    SCHEDULED = "scheduled"   # 예약됨
    PUBLISHED = "published"   # 배포됨
    CLOSED = "closed"         # 종료됨


class FormBase(SQLModel):
    uuid: str = Field(max_length=36, unique=True, index=True)
    category: str = Field(min_length=1, max_length=255)
    title: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=255)
    JSONSchema: Dict[str, Any] = Field(default={}, sa_column=Column(JSON))
    UISchema: Dict[str, Any] = Field(default={}, sa_column=Column(JSON))
    Theme: str = Field(default="mui")
    useYN: bool = Field(default=True)
    # 배포 관련 메타데이터
    publish_status: PublishStatus = Field(default=PublishStatus.DRAFT)
    publish_start_at: datetime.datetime | None = Field(default=None)
    publish_end_at: datetime.datetime | None = Field(default=None)
    max_responses: int | None = Field(default=None)  # 최대 응답 수 (None=무제한)
    allow_anonymous: bool = Field(default=True)  # 익명 응답 허용
    require_login: bool = Field(default=False)  # 로그인 필요 여부


class FormTemplate(FormBase, Base):
    pass


class FormTable(FormTemplate, table=True):
    # Relationships
    publishes: List["FormPublishTable"] = Relationship(back_populates="form")


class FormPublishBase(SQLModel):
    form_idx: int = Field(foreign_key="formtable.idx")
    receiver: str = Field(max_length=255)  # 이메일 또는 전화번호
    receiver_name: str | None = Field(default=None, max_length=100)  # 수신자 이름
    token: str = Field(max_length=64, unique=True, index=True)  # 접근 토큰
    expired_at: datetime.datetime = Field(default_factory=lambda: datetime.datetime.now() + datetime.timedelta(days=30))
    # 이메일 전송 관련
    is_email_sent: bool = Field(default=False)  # 이메일 전송 여부
    email_sent_at: datetime.datetime | None = Field(default=None)  # 이메일 전송 시간
    email_sent_count: int = Field(default=0)  # 이메일 전송 횟수
    # 응답 관련
    is_submitted: bool = Field(default=False)  # 제출 여부
    submitted_at: datetime.datetime | None = Field(default=None)  # 제출 시간
    responseSchema: Dict[str, Any] = Field(default={}, sa_column=Column(JSON))


class FormPublishTemplate(FormPublishBase, Base): 
    pass
    

class FormPublishTable(FormPublishTemplate, table=True):
    # Relationships
    form: FormTable = Relationship(back_populates="publishes")
