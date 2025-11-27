from typing import List, Tuple, Any
from sqlalchemy import ColumnElement
from sqlalchemy.orm import aliased
from sqlmodel import SQLModel

class PathResolver:
    """중첩 경로 해석 클래스"""
    
    def __init__(self, model: type[SQLModel]):
        self.model = model
        self.joins = {}  # 조인 정보 저장 {join_path: alias}
        self.join_counter = 0  # 별칭 생성용 카운터
    
    def resolve_nested_path(self, path: str) -> Tuple[ColumnElement, List[Tuple]]:
        """중첩된 경로를 해석하여 최종 컬럼과 필요한 조인들을 반환"""
        if "." not in path:
            # 단순 경로
            if hasattr(self.model, path):
                return getattr(self.model, path), []
            else:
                raise ValueError(f"속성 '{path}'가 모델에 존재하지 않습니다")
        
        parts = path.split(".")
        current_model = self.model
        join_path_parts = []
        aliases_needed = []
        
        # 관계를 따라 이동하면서 조인 경로 구성
        for i, part in enumerate(parts[:-1]):  # 마지막 속성 제외
            if not hasattr(current_model, part):
                raise ValueError(f"관계 '{part}'가 모델 '{current_model.__name__}'에 존재하지 않습니다")
            
            attr = getattr(current_model, part)
            
            # 관계 속성인지 확인
            if not hasattr(attr.property, 'mapper'):
                raise ValueError(f"'{part}'는 관계 속성이 아닙니다")
            
            # 조인 경로 구성
            join_path_parts.append(part)
            join_path = ".".join(join_path_parts)
            
            # 이미 조인이 생성되어 있는지 확인
            if join_path not in self.joins:
                # 새로운 별칭 생성
                target_model = attr.property.mapper.class_
                alias = aliased(target_model, name=f"alias_{self.join_counter}")
                self.joins[join_path] = alias
                self.join_counter += 1
                aliases_needed.append((attr, alias, join_path))
            
            # 다음 모델로 이동
            current_model = attr.property.mapper.class_
        
        # 최종 속성 확인
        final_attr = parts[-1]
        if not hasattr(current_model, final_attr):
            raise ValueError(f"속성 '{final_attr}'가 모델 '{current_model.__name__}'에 존재하지 않습니다")
        
        # 최종 컬럼 반환 (별칭이 있으면 별칭 사용)
        if join_path_parts:
            final_join_path = ".".join(join_path_parts)
            if final_join_path in self.joins:
                final_alias = self.joins[final_join_path]
                column = getattr(final_alias, final_attr)
            else:
                column = getattr(current_model, final_attr)
        else:
            column = getattr(current_model, final_attr)
        
        return column, aliases_needed 