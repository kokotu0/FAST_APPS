"""
모델 검사기

SQLModel의 관계, 컬럼, 스키마 정보를 추출하고 분석합니다.
"""

from typing import Type, Dict, Set, Optional, get_args, get_origin, Union
from sqlmodel import SQLModel
from sqlalchemy import inspect
from sqlalchemy.orm import RelationshipProperty
from core.base.CRUD.crud_types import RequestModel
import logging

logger = logging.getLogger(__name__)

class ModelInspector:
    """모델 검사 및 정보 추출 클래스"""
    
    @staticmethod
    def get_relationships(model: Type[SQLModel]) -> Dict[str, RelationshipProperty]:
        """
        모델의 관계 속성 추출
        
        Args:
            model: 검사할 모델 클래스
            
        Returns:
            관계 속성 딕셔너리 {관계명: RelationshipProperty}
        """
        try:
            mapper = inspect(model)
            relationships = {rel.key: rel for rel in mapper.relationships}
            logger.debug(f"모델 {model.__name__}의 관계 {len(relationships)}개 추출")
            return relationships
        except Exception as e:
            logger.error(f"관계 추출 실패 ({model.__name__}): {e}")
            return {}

    @staticmethod
    def get_columns(model: Type[SQLModel]) -> Set[str]:
        """
        모델의 컬럼 이름 추출
        
        Args:
            model: 검사할 모델 클래스
            
        Returns:
            컬럼 이름 집합
        """
        try:
            mapper = inspect(model)
            columns = {col.key for col in mapper.columns}
            logger.debug(f"모델 {model.__name__}의 컬럼 {len(columns)}개 추출")
            return columns
        except Exception as e:
            logger.error(f"컬럼 추출 실패 ({model.__name__}): {e}")
            return set()

    @staticmethod
    def get_related_model(model: Type[SQLModel], relationship_key: str) -> Optional[Type[SQLModel]]:
        """
        관계에서 연결된 모델 클래스 추출
        
        Args:
            model: 기준 모델 클래스
            relationship_key: 관계 키
            
        Returns:
            연결된 모델 클래스 (없으면 None)
        """
        try:
            mapper = inspect(model)
            relationship = mapper.relationships.get(relationship_key)
            if relationship:
                related_model = relationship.mapper.class_
                logger.debug(f"관계 {relationship_key}의 연결 모델: {related_model.__name__}")
                return related_model
            else:
                logger.warning(f"관계 {relationship_key}를 찾을 수 없음 (모델: {model.__name__})")
                return None
        except Exception as e:
            logger.error(f"관련 모델 추출 실패 ({model.__name__}.{relationship_key}): {e}")
            return None
    
    @staticmethod
    def get_base_schema(request_schema: RequestModel, relationship_key: str) -> Type[SQLModel]:
        """
        Request 스키마에서 relationship의 Base 스키마 추출
        
        Args:
            request_schema: Request 스키마 클래스
            relationship_key: 관계 키
            
        Returns:
            Base 스키마 클래스
            
        Raises:
            ValueError: 스키마 추출 실패 시
            
        Example:
            AuthorRequest.articles → List[ArticleBase] → ArticleBase
        """
        logger.debug(f"Base 스키마 추출 시도: {request_schema.__name__}.{relationship_key}")
        
        # request_schema의 model_fields에서 relationship_key의 타입 가져오기
        field_info = request_schema.model_fields.get(relationship_key)
        if not field_info or not hasattr(field_info, 'annotation'):
            raise ValueError(f"{relationship_key}: field_info 또는 annotation 없음")
            
        field_type = field_info.annotation
        logger.debug(f"필드 타입: {field_type}")
        
        # List[ArticleBase], Optional[List[ArticleBase]] 등 처리
        origin = get_origin(field_type)
        logger.debug(f"Origin: {origin}")
        
        # Optional[List[...]]인 경우 내부 추출
        if origin is Union:
            args = get_args(field_type)
            for arg in args:
                if arg is not type(None) and get_origin(arg) is list:
                    field_type = arg
                    origin = list
                    break
        
        if origin is list:
            args = get_args(field_type)
            logger.debug(f"List args: {args}")
            if args and len(args) > 0:
                base_schema = args[0]
                logger.debug(f"✓ Base 스키마 추출 성공: {base_schema.__name__}")
                return base_schema
        
        logger.error(f"Base 스키마 추출 실패: origin={origin}")
        raise ValueError(f"{relationship_key}: Base 스키마 추출 실패")

    @staticmethod
    def get_relationship_direction(model: Type[SQLModel], relationship_key: str) -> Optional[str]:
        """
        관계의 방향 정보 추출
        
        Args:
            model: 모델 클래스
            relationship_key: 관계 키
            
        Returns:
            관계 방향 ('ONETOMANY', 'ONETOONE', 'MANYTOONE', 'MANYTOMANY')
        """
        try:
            relationships = ModelInspector.get_relationships(model)
            relationship = relationships.get(relationship_key)
            if relationship:
                direction = relationship.direction.name
                logger.debug(f"관계 {relationship_key}의 방향: {direction}")
                return direction
            return None
        except Exception as e:
            logger.error(f"관계 방향 추출 실패 ({model.__name__}.{relationship_key}): {e}")
            return None

    @staticmethod
    def has_soft_delete_column(model: Type[SQLModel], column_name: str = "deleted") -> bool:
        """
        모델이 soft delete 컬럼을 가지고 있는지 확인
        
        Args:
            model: 검사할 모델 클래스
            column_name: soft delete 컬럼명
            
        Returns:
            soft delete 컬럼 존재 여부
        """
        columns = ModelInspector.get_columns(model)
        has_column = column_name in columns
        logger.debug(f"모델 {model.__name__}의 {column_name} 컬럼 존재: {has_column}")
        return has_column

    @staticmethod
    def get_primary_key_fields(model: Type[SQLModel]) -> Set[str]:
        """
        모델의 기본 키 필드들 추출
        
        Args:
            model: 검사할 모델 클래스
            
        Returns:
            기본 키 필드 이름 집합
        """
        try:
            mapper = inspect(model)
            pk_fields = {col.key for col in mapper.primary_key}
            logger.debug(f"모델 {model.__name__}의 기본 키: {pk_fields}")
            return pk_fields
        except Exception as e:
            logger.error(f"기본 키 추출 실패 ({model.__name__}): {e}")
            return set()

    @staticmethod
    def is_relationship_nullable(model: Type[SQLModel], relationship_key: str) -> bool:
        """
        관계가 nullable인지 확인
        
        Args:
            model: 모델 클래스
            relationship_key: 관계 키
            
        Returns:
            nullable 여부
        """
        try:
            relationships = ModelInspector.get_relationships(model)
            relationship = relationships.get(relationship_key)
            if relationship:
                # 외래 키 컬럼의 nullable 속성 확인
                for column in relationship.local_columns:
                    if not column.nullable:
                        return False
                return True
            return False
        except Exception as e:
            logger.error(f"관계 nullable 확인 실패 ({model.__name__}.{relationship_key}): {e}")
            return False

    @staticmethod
    def get_mapper(model: Type[SQLModel]):
        """
        모델의 SQLAlchemy mapper 반환
        
        Args:
            model: 검사할 모델 클래스
            
        Returns:
            SQLAlchemy mapper 객체
        """
        return inspect(model)

    @staticmethod
    def get_table_name(model: Type[SQLModel]) -> str:
        """
        모델의 테이블 이름 반환
        
        Args:
            model: 검사할 모델 클래스
            
        Returns:
            테이블 이름
        """
        try:
            mapper = inspect(model)
            return mapper.local_table.name
        except Exception as e:
            logger.error(f"테이블 이름 추출 실패 ({model.__name__}): {e}")
            return model.__name__.lower()