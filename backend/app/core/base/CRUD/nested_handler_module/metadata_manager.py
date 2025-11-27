"""
메타데이터 관리자

생성/수정 시간, 생성자/수정자 등의 메타데이터를 자동으로 관리합니다.
"""

from datetime import datetime
from typing import TYPE_CHECKING, Optional
from sqlmodel import SQLModel
from .types import ProcessedData
from .utils import safe_setattr
import logging

if TYPE_CHECKING:
    from core.base import UserOut

logger = logging.getLogger(__name__)

class MetadataManager:
    """메타데이터 자동 관리 클래스"""
    
    def __init__(self, user: 'UserOut'):
        """
        Args:
            user: 현재 사용자 정보
        """
        self.user = user
        
    def add_creation_metadata(self, data: ProcessedData) -> None:
        """
        생성 시 메타데이터 자동 추가
        
        Args:
            data: 처리할 데이터 딕셔너리
        """
        # created_at은 Base 클래스에서 default_factory로 자동 설정되므로 
        # 명시적으로 설정하지 않음 (이미 설정된 경우만 유지)
        if "created_at" not in data:
            data["created_at"] = datetime.now()
            
        # created_by 설정
        if self.user and hasattr(self.user, 'idx'):
            data["created_by"] = self.user.idx
            
        # updated_at과 updated_by는 생성 시에는 None으로 유지
        # (업데이트 시에만 설정)
        logger.debug(f"생성 메타데이터 추가 완료: created_by={data.get('created_by')}")

    def add_update_metadata(self, data: ProcessedData) -> None:
        """
        업데이트 시 메타데이터 자동 추가
        
        Args:
            data: 처리할 데이터 딕셔너리
        """
        # updated_at 항상 현재 시간으로 설정
        data["updated_at"] = datetime.now()
        
        # updated_by 설정
        if self.user and hasattr(self.user, 'idx'):
            data["updated_by"] = self.user.idx
            
        logger.debug(f"업데이트 메타데이터 추가 완료: updated_by={data.get('updated_by')}")

    def update_instance_metadata(self, instance: SQLModel) -> None:
        """
        인스턴스의 메타데이터 직접 업데이트
        
        Args:
            instance: 업데이트할 모델 인스턴스
        """
        # updated_at 항상 현재 시간으로 설정
        if safe_setattr(instance, 'updated_at', datetime.now()):
            logger.debug("updated_at 설정 완료")
        
        # updated_by 설정
        if self.user and hasattr(self.user, 'idx'):
            if safe_setattr(instance, 'updated_by', self.user.idx):
                logger.debug(f"updated_by 설정 완료: {self.user.idx}")

    def add_soft_delete_metadata(self, instance: SQLModel, soft_delete_column: str) -> None:
        """
        Soft delete 시 메타데이터 추가
        
        Args:
            instance: 삭제할 모델 인스턴스
            soft_delete_column: soft delete 컬럼명
        """
        # soft delete 플래그 설정
        if safe_setattr(instance, soft_delete_column, True):
            logger.debug(f"Soft delete 플래그 설정: {soft_delete_column}=True")
            
        # 메타데이터 업데이트
        self.update_instance_metadata(instance)
        
    def restore_soft_deleted_metadata(self, instance: SQLModel, soft_delete_column: str) -> None:
        """
        Soft delete 복구 시 메타데이터 업데이트
        
        Args:
            instance: 복구할 모델 인스턴스
            soft_delete_column: soft delete 컬럼명
        """
        # soft delete 플래그 해제
        if safe_setattr(instance, soft_delete_column, False):
            logger.debug(f"Soft delete 플래그 해제: {soft_delete_column}=False")
            
        # 메타데이터 업데이트
        self.update_instance_metadata(instance)

    def get_metadata_fields(self) -> set:
        """메타데이터 필드 목록 반환"""
        return {
            'created_at', 'updated_at', 
            'created_by', 'updated_by'
        }
        
    def should_exclude_from_comparison(self, field_name: str) -> bool:
        """비교에서 제외해야 할 메타데이터 필드인지 확인"""
        metadata_fields = self.get_metadata_fields()
        return field_name in metadata_fields
















