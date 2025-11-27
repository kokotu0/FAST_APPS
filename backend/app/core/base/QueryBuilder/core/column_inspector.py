from typing import Optional, Union, Literal, List, Dict, Any
from sqlalchemy import ColumnElement
from sqlalchemy.inspection import inspect
from sqlalchemy.orm import RelationshipProperty
from datetime import datetime, date
from sqlmodel import SQLModel
from enum import Enum

ColumnType = Literal['text', 'number', 'date', 'boolean', 'relation']

class PathInfo:
    """경로 분석 결과를 담는 클래스"""
    def __init__(self, path: str, column_type: ColumnType, is_nested: bool = False):
        self.path = path
        self.column_type = column_type
        self.is_nested = is_nested
        self.relationships: List[Dict] = []
        self.final_model: Optional[type] = None
        self.final_attribute: Optional[str] = None
        self.sqlalchemy_column: Optional[ColumnElement] = None

class ColumnInspector:
    """컬럼 타입 감지 및 경로 분석 클래스"""
    
    def __init__(self, model: type[SQLModel]):
        self.model = model
        self.columns = {col.name: col for col in inspect(model).columns}
        self.relations = {rel: value for rel, value in model.__sqlmodel_relationships__.items()}
        self._inspector = inspect(model)
    
    def analyze_path(self, path: str) -> PathInfo:
        """경로를 분석하여 PathInfo 반환"""
        path_parts = path.split('.')
        
        if len(path_parts) == 1:
            # 단일 속성
            return self._analyze_single_attribute(path_parts[0])
        else:
            # 중첩 경로
            return self._analyze_nested_path(path_parts)
    
    def _analyze_single_attribute(self, attr_name: str) -> PathInfo:
        """단일 속성 분석"""
        # 일반 컬럼인 경우
        if attr_name in self.columns:
            column = self.columns[attr_name]
            column_type = self._get_sqlalchemy_column_type(column)
            
            path_info = PathInfo(attr_name, column_type, False)
            path_info.sqlalchemy_column = column
            path_info.final_model = self.model
            path_info.final_attribute = attr_name
            return path_info
        
        # 관계인 경우
        elif attr_name in self.relations:
            cardinality = self._get_relation_cardinality(attr_name)
            
            path_info = PathInfo(attr_name, 'relation', False)
            path_info.relationships = [{
                'name': attr_name,
                'cardinality': cardinality,
                'model': self.model.__name__
            }]
            path_info.final_model = self._get_related_model(attr_name)
            path_info.final_attribute = attr_name
            return path_info
        
        else:
            raise ValueError(f"속성 {attr_name}가 {self.model.__name__}에 존재하지 않습니다.")
    
    def _analyze_nested_path(self, path_parts: List[str]) -> PathInfo:
        """중첩 경로 분석"""
        current_model = self.model
        current_inspector = self
        relationships = []
        
        # 마지막 속성을 제외한 모든 경로는 관계여야 함
        for i, part in enumerate(path_parts[:-1]):
            if part not in current_inspector.relations:
                raise ValueError(f"관계 {part}가 {current_model.__name__}에 존재하지 않습니다.")
            
            # 관계 정보 수집
            cardinality = current_inspector._get_relation_cardinality(part)
            relationships.append({
                'name': part,
                'cardinality': cardinality,
                'model': current_model.__name__
            })
            
            # 다음 모델로 이동
            try:
                current_model = current_inspector._get_related_model(part)
                current_inspector = ColumnInspector(current_model)
            except Exception as e:
                raise ValueError(f"관계 {part}의 대상 모델을 찾을 수 없습니다: {e}")
        
        # 마지막 속성 분석
        final_attr = path_parts[-1]
        final_path_info = current_inspector._analyze_single_attribute(final_attr)
        
        # 중첩 경로 정보 구성
        full_path = '.'.join(path_parts)
        path_info = PathInfo(full_path, final_path_info.column_type, True)
        path_info.relationships = relationships
        path_info.final_model = current_model
        path_info.final_attribute = final_attr
        path_info.sqlalchemy_column = final_path_info.sqlalchemy_column
        
        return path_info
    
    def get_column_type_from_element(self, column_element: ColumnElement) -> ColumnType:
        """SQLAlchemy ColumnElement에서 타입 추출"""
        if hasattr(column_element, 'type'):
            return self._get_sqlalchemy_column_type(column_element)
        elif hasattr(column_element, 'name'):
            # 컬럼 이름으로 다시 조회
            return self.analyze_path(column_element.name).column_type
        else:
            return 'text'  # 기본값
    
    def _get_sqlalchemy_column_type(self, column) -> ColumnType:
        """SQLAlchemy 컬럼의 타입을 분석"""
        column_type_str = str(column.type).lower()
        
        # 정수형
        if any(t in column_type_str for t in ['integer', 'int', 'bigint', 'smallint']):
            return 'number'
        # 실수형
        elif any(t in column_type_str for t in ['float', 'real', 'double', 'decimal', 'numeric']):
            return 'number'
        # 날짜/시간형
        elif any(t in column_type_str for t in ['datetime', 'date', 'time', 'timestamp']):
            return 'date'
        # 불린형
        elif any(t in column_type_str for t in ['boolean', 'bool']):
            return 'boolean'
        # 기본값은 텍스트
        else:
            return 'text'
    
    def _get_relation_cardinality(self, relation_name: str) -> str:
        """관계의 카디널리티를 반환"""
        if relation_name not in self.relations:
            raise ValueError(f"관계 {relation_name}가 존재하지 않습니다.")
        
        relationship = self.relations[relation_name]
        
        # 1. 일반적인 SQLModel Relationship 처리
        if hasattr(relationship, 'sa_relationship') and relationship.sa_relationship is not None:
            sa_rel = relationship.sa_relationship
            current_is_list = sa_rel.uselist
            
            # back_populates 확인
            if hasattr(sa_rel, 'back_populates') and sa_rel.back_populates:
                try:
                    related_model = sa_rel.entity.class_
                    if hasattr(related_model, '__sqlmodel_relationships__'):
                        back_rel_name = sa_rel.back_populates
                        if back_rel_name in related_model.__sqlmodel_relationships__:
                            back_relationship = related_model.__sqlmodel_relationships__[back_rel_name]
                            if hasattr(back_relationship, 'sa_relationship') and back_relationship.sa_relationship:
                                back_sa_rel = back_relationship.sa_relationship
                                back_is_list = back_sa_rel.uselist
                                
                                if not current_is_list and not back_is_list:
                                    return '1:1'
                                elif not current_is_list and back_is_list:
                                    return 'N:1'
                                elif current_is_list and not back_is_list:
                                    return '1:N'
                                else:
                                    return 'N:N'
                except Exception as e:
                    print(f"back_populates 분석 실패: {e}")
            
            # fallback
            return '1:N' if current_is_list else 'N:1'
        
        # 2. sa_relationship_kwargs를 사용한 경우의 fallback
        try:
            mapper = inspect(self.model)
            if hasattr(mapper, 'relationships') and relation_name in mapper.relationships:
                sa_relationship = mapper.relationships[relation_name]
                current_is_list = sa_relationship.uselist
                
                # 외래키를 통한 추정
                if hasattr(sa_relationship, 'direction'):
                    try:
                        from sqlalchemy.orm import MANYTOONE, ONETOMANY, MANYTOMANY
                        # ONETOONE은 최신 버전에만 있으므로 제외
                        direction = sa_relationship.direction
                        
                        if direction == MANYTOONE:
                            return 'N:1'
                        elif direction == ONETOMANY:
                            return '1:N' 
                        elif direction == MANYTOMANY:
                            return 'N:N'
                        # ONETOONE 처리는 다른 방식으로
                        elif str(direction).endswith('ONETOONE'):
                            return '1:1'
                    except ImportError:
                        # direction 상수들을 import할 수 없는 경우
                        pass
                
                # uselist로 추정
                return '1:N' if current_is_list else 'N:1'
                
        except Exception as e:
            print(f"SQLAlchemy mapper로 카디널리티 분석 실패: {e}")
            pass  # 에러 메시지만 출력하고 계속 진행
        # 3. 타입 힌트로 추정
        try:
            if hasattr(self.model, '__annotations__'):
                annotation = self.model.__annotations__.get(relation_name)
                if annotation:
                    if hasattr(annotation, '__origin__') and annotation.__origin__ in (list, List):
                        return '1:N'
                    else:
                        return 'N:1'  # 단일 객체로 추정
        except Exception as e:
            print(f"타입 힌트로 카디널리티 분석 실패: {e}")
        
        # 4. 외래키 필드 존재 여부로 추정
        try:
            # 현재 모델에 {relation_name}_idx 또는 {relation_name}_id 필드가 있으면 N:1
            fk_field_names = [f"{relation_name}_idx", f"{relation_name}_id", f"{relation_name.rstrip('s')}_id"]
            for fk_name in fk_field_names:
                if fk_name in self.columns:
                    return 'N:1'
        except Exception:
            pass
        
        print(f"관계 {relation_name}의 카디널리티를 확정할 수 없음, N:1로 추정")
        return 'N:1'  # 기본값
    
    def _get_related_model(self, relation_name: str) -> type[SQLModel]:
        """관계의 대상 모델을 반환"""
        if relation_name not in self.relations:
            raise ValueError(f"관계 {relation_name}가 존재하지 않습니다.")
        
        relationship = self.relations[relation_name]
        
        # 일반적인 SQLModel Relationship
        if hasattr(relationship, 'sa_relationship') and relationship.sa_relationship is not None:
            if hasattr(relationship.sa_relationship, 'entity'):
                return relationship.sa_relationship.entity.class_
        
        # sa_relationship_kwargs를 사용한 경우의 fallback
        # SQLAlchemy inspector를 통해 관계 정보 확인
        try:
            mapper = inspect(self.model)
            if hasattr(mapper, 'relationships') and relation_name in mapper.relationships:
                sa_relationship = mapper.relationships[relation_name]
                if hasattr(sa_relationship, 'entity'):
                    return sa_relationship.entity.class_
        except Exception as e:
            print(f"SQLAlchemy inspector로 관계 분석 실패: {e}")
        
        # 타입 힌트에서 추출 시도
        try:
            if hasattr(self.model, '__annotations__'):
                annotation = self.model.__annotations__.get(relation_name)
                if annotation and hasattr(annotation, '__origin__'):
                    # List[Model] 형태인 경우
                    if annotation.__origin__ in (list, List):
                        return annotation.__args__[0]
                elif annotation and isinstance(annotation, type):
                    # 직접 Model 타입인 경우
                    return annotation
        except Exception as e:
            print(f"타입 힌트에서 관계 모델 추출 실패: {e}")
        
        raise ValueError(f"관계 {relation_name}의 대상 모델을 찾을 수 없습니다: sa_relationship이 None이거나 접근할 수 없습니다.")
    
    def get_available_paths(self, max_depth: int = 2) -> List[str]:
        """사용 가능한 모든 경로를 반환 (디버깅/문서화용)"""
        paths = []
        
        # 직접 컬럼들
        paths.extend(self.columns.keys())
        
        # 관계들 (1단계)
        for rel_name in self.relations.keys():
            paths.append(rel_name)
            
            # 중첩 관계들 (지정된 깊이만큼)
            if max_depth > 1:
                try:
                    cardinality = self._get_relation_cardinality(rel_name)
                    if cardinality in ['1:1', 'N:1']:  # 단일 객체 관계만
                        related_model = self._get_related_model(rel_name)
                        related_inspector = ColumnInspector(related_model)
                        
                        # 관련 모델의 컬럼들
                        for col_name in related_inspector.columns.keys():
                            paths.append(f"{rel_name}.{col_name}")
                        
                        # 더 깊은 관계들 (재귀적으로 처리 가능)
                        if max_depth > 2:
                            for nested_rel in related_inspector.relations.keys():
                                nested_cardinality = related_inspector._get_relation_cardinality(nested_rel)
                                if nested_cardinality in ['1:1', 'N:1']:
                                    paths.append(f"{rel_name}.{nested_rel}")
                                    
                except Exception:
                    continue
        
        return sorted(paths)

# 사용 예시
"""
inspector = ColumnInspector(User)

# 경로 분석
path_info = inspector.analyze_path("user.profile.bio")
print(f"타입: {path_info.column_type}")
print(f"중첩 여부: {path_info.is_nested}")
print(f"관계 체인: {path_info.relationships}")

# 사용 가능한 모든 경로 확인
available_paths = inspector.get_available_paths()
print(f"사용 가능한 경로들: {available_paths}")
"""