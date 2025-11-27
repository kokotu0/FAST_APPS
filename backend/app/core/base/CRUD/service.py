import copy
import datetime
import json
import logging
import traceback
from typing import (
    Any,
    Callable,
    Dict,
    Generic,
    List,
    Literal,
    Optional,
    Sequence,
    Set,
    Tuple,
    TypeVar,
    Union,
    cast,
    overload,
)
from typing import Annotated, Type
from urllib.parse import unquote

from fastapi import Depends, HTTPException, Query, Response
from sqlalchemy import Select, delete, func, inspect
from sqlalchemy.exc import NoResultFound
from sqlalchemy.orm import RelationshipProperty
from sqlmodel import SQLModel, Session, col, delete, insert, select, update
from sqlmodel.sql._expression_select_cls import SelectOfScalar
from typing_extensions import deprecated

from api.user.schemas import UserOut
from core.base import QueryBuilder
from core.base.CRUD.schemas import StandardResponse, StandardResponseMeta
from core.base.CRUD.crud_types import ModelType, RequestModel, ResponseModel
from core.base.CRUD.types import ServiceProtocol
from core.database import SessionDep
from core.internal.Authenticate import auth_get_current_user
from core.internal.filter import RelationFilter
from core.internal.sort import RelationSort
from core.state_machine.base import StateMachine

from .nested_handler_module import NestedRelationshipHandler

# 일반적인 상황에서 1:1 nested는 발생하지 않아 아직 미구현상태지만, 차차 구현할 것.
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class CRUDService(
    Generic[ModelType, RequestModel, ResponseModel],
    ServiceProtocol[ModelType, RequestModel, ResponseModel],
):
    request_model: RequestModel
    response_model: ResponseModel

    def __init__(
        self,
        model: Type[ModelType],
        request_model: Type[RequestModel] | None = None,
        response_model: Type[ResponseModel] | None = None,
        deleted_column: Optional[str] = None,
        # 관계별 키 필드 및 제외 필드 설정
        relationship_key_fields: Dict[str, Set[str]] = dict(),
        relationship_exclude_fields: Dict[str, Set[str]] = dict(),
        relationship_deleted_columns: Dict[str, str] = dict(),
        state_machine_validate: Dict[
            str, StateMachine
        ] = dict(),  # 상태전이 : key : model의 key, value : StateMachine
        **kwargs,
    ):
        self.model = model
        self.response_model = cast(
            ResponseModel, response_model if response_model else model
        )
        self.request_model = cast(
            RequestModel, request_model if request_model else model
        )
        self.nested_handler = None  # POST 메서드에서 세션과 함께 초기화
        # 관계별 설정 저장
        if deleted_column is not None:
            self.is_soft_delete = True
            self.deleted_column = deleted_column
        else:
            self.is_soft_delete = False
            self.deleted_column = None  # 기본값 설정
        self.relationship_key_fields = relationship_key_fields
        self.relationship_exclude_fields = relationship_exclude_fields
        self.relationship_deleted_columns = relationship_deleted_columns

        self.state_machine_validate = state_machine_validate

    def get_by_idx(
        self, session: Session, User: UserOut, idx: int, load_deleted: bool = False
    ) -> ResponseModel:

        if not hasattr(self.model, "idx"):
            raise HTTPException(status_code=400, detail="Model has no idx field")

        result = session.get(
            self.model,
            idx,
        )

        if not result:
            raise HTTPException(status_code=404, detail="Item not found")

        if (
            not load_deleted
            and self.is_soft_delete
            and self.deleted_column
            and hasattr(result, self.deleted_column)
        ):
            is_deleted = bool(getattr(result, self.deleted_column))
            if is_deleted:
                raise HTTPException(status_code=404, detail="Item is deleted")

        # model_validate로 lazy loading 조기 실행 (세션이 열려있을 때)
        validated_result = self.response_model.model_validate(result)
        
        filtered_result = copy.deepcopy(validated_result)
        
        # Python 레벨에서 관계 deleted 필터링
        if (
            self.relationship_deleted_columns
            and self.is_soft_delete
            and load_deleted is not True
        ):
            for (
                relationship_name,
                deleted_column,
            ) in self.relationship_deleted_columns.items():
                related_items = getattr(filtered_result, relationship_name)
                if related_items:
                    if isinstance(related_items, list):
                        related_items = [
                            rel
                            for rel in related_items
                            if not getattr(rel, deleted_column, False)
                        ]
                        # idx 기준 내림차순 정렬
                        related_items.sort(key=lambda x: getattr(x, 'idx', 0), reverse=False)
                    else:
                        if getattr(related_items, deleted_column, False):
                            related_items = None
                    setattr(filtered_result, relationship_name, related_items)
        
        return filtered_result

    def get_state_machine(
        self,
    ):
        return {
            state_col: state_machine.get_machine_info()
            for state_col, state_machine in self.state_machine_validate.items()
        }

    def get_standard_response(
        self,
        session: SessionDep,
        User: UserOut,
        request_json: Optional[str] = None,
        load_deleted: bool = False,
    ) -> StandardResponse[Sequence[ResponseModel]]:
        # soft delete 체크
        if (
            load_deleted is True
            and self.deleted_column
            and not hasattr(self.model, self.deleted_column)
        ):
            raise HTTPException(
                status_code=400, detail="이 모델은 soft delete를 지원하지 않습니다"
            )

        builder = QueryBuilder(model=self.model, request_json=request_json)

        # soft delete가 활성화되어 있고 load_deleted가 True가 아니면 deleted=False인 항목만 조회
        if self.is_soft_delete and load_deleted is not True:
            if self.deleted_column and hasattr(self.model, self.deleted_column):
                # 메인 모델만 필터링 (관계는 Python 레벨에서 처리)
                builder.add_column_filter(self.deleted_column, "equals", load_deleted)
                builder = builder.apply_table_request()
                query = builder.build()
                logger.debug(query.compile(compile_kwargs={"literal_binds": True}))
                assert builder.row_count_query is not None
                row_count = session.exec(builder.row_count_query).one()
            else:
                raise HTTPException(
                    status_code=400,
                    detail=f"테이블에 {self.deleted_column} 필드가 없습니다.",
                )
        else:
            builder = builder.apply_table_request()
            query = builder.build()
            assert builder.row_count_query is not None
            row_count = session.exec(builder.row_count_query).one()
        # 결과 조회
        results = session.exec(query).all()
        # model_validate로 lazy loading 조기 실행 (세션이 열려있을 때)
        results = [self.response_model.model_validate(result) for result in results]
        
        filtered_results = copy.deepcopy(results)
        
        # Python 레벨에서 관계 deleted 필터링 (1:N 중복 제거)
        if (
            self.relationship_deleted_columns
            and self.is_soft_delete
            and load_deleted is not True
        ):
            for item in filtered_results:  # 부모는 루프 유지
                for (
                    relationship_name,
                    deleted_column,
                ) in self.relationship_deleted_columns.items():
                    related_items = getattr(item, relationship_name)
                    if related_items:
                        if isinstance(related_items, list):
                            related_items = [
                                rel
                                for rel in related_items
                                if not getattr(rel, deleted_column, False)
                            ]
                            # idx 기준 내림차순 정렬
                            related_items.sort(key=lambda x: getattr(x, 'idx', 0), reverse=False)
                        else:
                            if getattr(related_items, deleted_column, False):
                                related_items = None
                        setattr(item, relationship_name, related_items)
        
        return StandardResponse(
            success=True,
            message="Success",
            data=filtered_results,
            meta=StandardResponseMeta(
                total_count=row_count,
            ),
        )

    def validate_filters(self, filters: dict, allowed_cols=None, except_cols=None):
        # except_cols와 allowed_cols는 XOR 관계
        # XOR 관계 검증
        if allowed_cols and except_cols:
            raise ValueError("except_cols와 allowed_cols는 동시에 설정할 수 없습니다.")

        # 필터 검증
        valid_filters = {}

        # 허용된 필드 기반 필터링 (화이트리스트)
        if allowed_cols:
            for key, value in filters.items():
                if key in allowed_cols:
                    valid_filters[key] = value

            if not valid_filters and filters:
                allowed_cols_str = ", ".join(allowed_cols)
                raise HTTPException(
                    status_code=400,
                    detail=f"필터링에 허용된 필드가 아닙니다. 다음 필드만 사용 가능합니다: {allowed_cols_str}",
                )

            return valid_filters

        # 제외할 필드 기반 필터링 (블랙리스트)
        elif except_cols:
            for key, value in filters.items():
                if key not in except_cols:
                    valid_filters[key] = value

            if not valid_filters and filters:
                except_cols_str = ", ".join(except_cols)
                raise HTTPException(
                    status_code=400,
                    detail=f"필터링에 허용되지 않은 필드가 사용되었습니다. 다음 필드는 사용할 수 없습니다: {except_cols_str}",
                )

            return valid_filters

        # 아무 제약도 없는 경우
        return filters

    def post(
        self,
        session: SessionDep,
        item: RequestModel,
        User: UserOut,
    ) -> ResponseModel:

        for state_col, state_machine in self.state_machine_validate.items():
            if not state_machine.can_initialize(getattr(item, state_col)):
                raise HTTPException(
                    status_code=400, detail=f"상태 {state_col} 시작 불가"
                )

        item_data = item.model_dump(exclude={"idx"})

        # NestedRelationshipHandler 초기화 (관계별 설정 사용)
        nested_handler = NestedRelationshipHandler(
            session=session,
            user=User,
            relationship_key_fields=self.relationship_key_fields,
            relationship_exclude_fields=self.relationship_exclude_fields,
        )

        # 중첩 데이터를 포함한 인스턴스 생성
        instance = nested_handler.create_with_nested(self.model, item_data)
        session.flush()
        session.refresh(instance)
        return self.response_model.model_validate(instance)
        # return instance



    def put(
        self, session: SessionDep, idx: int, item: RequestModel, User: UserOut
    ) -> ResponseModel:
        """PUT: 전체 리소스 대체"""

        item_data = item.model_dump()

        # DB에서 기존 객체 조회
        db_item = session.get(self.model, idx)
        if not db_item:
            raise HTTPException(
                status_code=404, detail=f"Item with idx {idx} not found"
            )

        for state_col, state_machine in self.state_machine_validate.items():
            if not state_machine.can_transition(
                getattr(db_item, state_col), getattr(item, state_col)
            ):
                logger.error(
                    f"상태 {state_col} 전이 불가: {getattr(db_item, state_col)} -> {getattr(item, state_col)}"
                )
                raise HTTPException(
                    status_code=400, detail=f"상태 {state_col} 전이 불가"
                )

            # NestedRelationshipHandler 초기화 (관계별 설정 사용)
        nested_handler = NestedRelationshipHandler(
            session=session,
            user=User,
            relationship_key_fields=self.relationship_key_fields,
            relationship_exclude_fields=self.relationship_exclude_fields,
            relationship_deleted_columns=self.relationship_deleted_columns,
        )

        # 중첩 데이터를 포함한 업데이트
        instance = nested_handler.update_with_nested(
            db_item,
            item_data,
            self.request_model,  # Request 스키마를 세 번째 인자로 전달
        )
        session.flush()
        session.refresh(instance)
        return self.response_model.model_validate(instance)

    def delete(
        self,
        session: SessionDep,
        idx: int,
        User: UserOut,
    ) -> ResponseModel:
        """
        DELETE: 리소스 삭제 (soft delete 또는 hard delete)

        Args:
            session: DB 세션
            idx: 삭제할 아이템의 idx
            User: 현재 사용자
        """
        # 아이템 조회
        item = session.get(self.model, idx)
        is_soft_delete = self.is_soft_delete

        if not item:
            raise HTTPException(status_code=404, detail="idx not found")

        if not self.is_soft_delete:
            raise HTTPException(
                status_code=400, detail="이 모델은 soft delete를 지원하지 않습니다"
            )


        nested_handler = NestedRelationshipHandler(
            session=session,
            user=User,
            relationship_key_fields=self.relationship_key_fields,
            relationship_exclude_fields=self.relationship_exclude_fields,
            relationship_deleted_columns=self.relationship_deleted_columns,
        )

        # soft delete인 경우 deleted 컬럼 확인
        if (
            is_soft_delete
            and self.deleted_column
            and not hasattr(item, self.deleted_column)
        ):
            raise HTTPException(
                status_code=400,
                detail=f"테이블에 {self.deleted_column} 필드가 없습니다.",
            )

        # nested_handler로 삭제 처리 (중첩 관계 포함)
        deleted_item = nested_handler.delete_with_nested(
            instance=item,
            deleted_column=self.deleted_column or "",
            is_soft_delete=is_soft_delete,
        )

        session.flush()
        return self.response_model.model_validate(deleted_item)


    def restore(
        self,
        session: SessionDep,
        idx: int,
        User: UserOut,
    ) -> ResponseModel:
        """
        RESTORE: 리소스 복구 (soft delete 또는 hard delete)
        """
        item = session.get(self.model, idx)
        if not item:
            raise HTTPException(status_code=404, detail="idx not found")
        if not self.is_soft_delete:
            raise HTTPException(
                status_code=400, detail="이 모델은 restore를 지원하지 않습니다"
            )

        nested_handler = NestedRelationshipHandler(
            session=session,
            user=User,
            relationship_key_fields=self.relationship_key_fields,
            relationship_exclude_fields=self.relationship_exclude_fields,
            relationship_deleted_columns=self.relationship_deleted_columns,
        )

        restored_item = nested_handler.restore_with_nested(
            instance=item,
            deleted_column=self.deleted_column or "",
            is_soft_delete=self.is_soft_delete,
        )

        session.flush()
        return self.response_model.model_validate(restored_item)

    def get_unique_values(
        self, columns: List[str] | str, session: SessionDep
    ) -> List[Dict]:
        if type(columns) == str:
            columns = [columns]
        for column_name in columns:
            if not hasattr(self.model, column_name):
                raise ValueError(
                    f"Column '{column_name}' does not exist in model {self.model.__name__}"
                )
        # 선택한 컬럼들 가져오기
        selected_columns = [getattr(self.model, column_name) for column_name in columns]

        # 기본 쿼리 생성
        query = (
            select(*selected_columns).distinct().order_by(*selected_columns).order_by()
        )

        # 쿼리 실행
        result = session.exec(query).all()

        formatted_result = []
        for row in result:
            formatted_row = {}
            for i, column_name in enumerate(columns):
                formatted_row[column_name] = row[i]
            formatted_result.append(formatted_row)

        return formatted_result

    def generate_order_number(self, session: Session, col_name: str, prefix: str):
        if not col_name:
            raise ValueError("col_name is required")
        if not prefix:
            raise ValueError("prefix is required")
        """주문 번호 자동 생성"""
        today = datetime.datetime.now().strftime("%Y%m%d")
        last_order = session.exec(
            select(self.model)
            .where(col(getattr(self.model, col_name)).like(f"%{today}%"))
            .order_by(col(getattr(self.model, col_name)).desc())
        ).first()
        if last_order:
            last_seq = int(getattr(last_order, col_name)[-4:])
            new_seq = last_seq + 1
        else:
            new_seq = 1

        return f"{prefix}-{today}-{new_seq:04d}"
