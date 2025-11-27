from typing import Optional
from datetime import datetime
from sqlalchemy import Column, JSON
from sqlmodel import Field, SQLModel

class Base(SQLModel):
    """
    모든 모델의 기본 클래스
    
    공통 메타데이터 필드들을 포함:
    - idx: 기본 키
    - created_at: 생성 시간
    - updated_at: 수정 시간  
    - created_by: 생성자 ID
    - updated_by: 수정자 ID
    """
    
    idx:int = Field(default=None,  primary_key=True)
    created_at: Optional[datetime] = Field(default_factory=datetime.now, description="생성 시간")
    updated_at: Optional[datetime] = Field(default=None, description="수정 시간")
    created_by: Optional[int] = Field(default=None, description="생성자 사용자 ID")
    updated_by: Optional[int] = Field(default=None, description="수정자 사용자 ID")