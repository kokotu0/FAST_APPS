import json
from typing import Type, TypeVar
from urllib.parse import unquote

from sqlalchemy import desc
from sqlmodel import SQLModel, select
from sqlalchemy.orm import joinedload, aliased

ModelType = TypeVar("ModelType", bound=SQLModel)

class RelationSort:
    """관계 필드에 대한 정렬을 지원하는 유틸리티 클래스"""
    
    @staticmethod
    def apply_sorting(model_class: Type[ModelType], sort_data: list|None, query=None):
        """
        JSON 문자열로부터 정렬 적용 (중첩된 관계에 대한 정렬 지원)
        
        Parameters:
        - model_class: SQLModel 클래스
        - sort_json: 정렬 JSON 문자열 (예: [{"id": "medium_category.name", "desc": true}])
        - query: 기존 쿼리 (없으면 새로 생성)
        
        Returns:
        - 정렬이 적용된 SQLModel select 쿼리 객체
        """
        if query is None:
            query = select(model_class)
            if hasattr(model_class, 'idx'):
                query = query.order_by(desc(model_class.idx))
            
        if not sort_data:
            return query
        # 정렬 적용
        try:
            # 관계 필드 처리
            if "." in sort_data[0].get('id'):
                parts = sort_data[0].get('id').split(".")
                relation_parts, attr_name = parts[:-1], parts[-1]
                
                current_model = model_class
                alias = None
                
                # 관계 경로 처리 및 조인
                for i, part in enumerate(relation_parts):
                    relation = getattr(current_model, part)
                    related_model = relation.prop.mapper.class_
                    
                    # 별칭 생성 및 조인
                    current_alias = aliased(related_model)
                    
                    if i == 0:
                        query = query.outerjoin(current_alias, relation)
                    else:
                        prev_relation = getattr(current_model, part)
                        query = query.outerjoin(current_alias, prev_relation)
                    
                    current_model = related_model
                    alias = current_alias
                
                # 최종 컬럼 선택
                column = getattr(alias, attr_name)
                
            else:
                # 직접 컬럼 정렬
                column = getattr(model_class, sort_data[0].get('id'))
            
            # 정렬 방향 적용
            query = query.order_by(desc(column) if sort_data[0].get('desc') else column)
            
        except (AttributeError, KeyError) as e:
            # 오류 로깅
            print(f"정렬 적용 중 오류 발생: {e}")
            
        return query