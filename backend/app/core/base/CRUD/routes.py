from enum import Enum
from functools import partial
import json
import os

from typing import (
    Any,
    Callable,
    TypeVar,
    Generic,
    Type,
    List,
    Literal,
    Union,
    cast,
    overload,
    Protocol,
    runtime_checkable,
    Optional,
    Dict,
    Set,
)
from fastapi import APIRouter, HTTPException, Query, Depends, Response
from sqlalchemy.util import deprecated
from sqlmodel import SQLModel, Session
from pydantic import BaseModel
from typing import Sequence
from api.user.schemas import UserOut
from core.base import QueryBuilder
from core.base.CRUD.schemas import (
    StandardResponse,
    StandardResponseMeta,
    StateMachineResponse,
)
from core.base.CRUD.crud_types import ModelType, RequestModel, ResponseModel
from core.base.CRUD.types import ServiceProtocol
from core.database import SessionDep
from core.base.CRUD.service import CRUDService
from core.exceptions import handle_error
from core.internal.Authenticate import auth_get_current_user

# 만약 기본 서비스(read, create,update,delete) 만 필요할 경우엔 router만 선언해도 자동으로 default service가 따라감.
# 만약 crud한 기능이 없는 router를 구현하더라도(굉장히 일부에 한하겠으나) 무조건적으로 CRUDRouter를 만들어주어야함.
# 형식의 일관성을 위함.
from sqlmodel.sql._expression_select_cls import SelectOfScalar

from core.state_machine.base import StateMachine

# 타입 변수 선언
S = TypeVar("S", bound=CRUDService)


routesType = Literal[
    "GET",
    "POST",
    "PUT",
    "PATCH",
    "DELETE",
    "get",
    "post",
    "put",
    "patch",
    "delete",
    "RELATION_GET",
    "relation_get",
]


class CRUDRouter(Generic[ModelType, RequestModel, ResponseModel]):
    """
    CRUD 작업을 위한 제네릭 라우터 클래스

    타입 매개변수:
        T: 데이터베이스 모델 타입
        S: 서비스 클래스 타입

    매개변수:
        model_type: 모델 클래스
        service_type: 서비스 클래스
    """

    def __init__(
        self,
        ModelType: Type[ModelType],
        service: (
            Callable[[], ServiceProtocol[ModelType, RequestModel, ResponseModel]]
            | ServiceProtocol[ModelType, RequestModel, ResponseModel]
            | CRUDService[ModelType, RequestModel, ResponseModel]
            | Callable[[], CRUDService[ModelType, RequestModel, ResponseModel]]
            | None
        ) = None,
        state_machine_validate: Dict[str, StateMachine] = dict(),
        response_model: Type[ResponseModel] | None = None,
        request_model: Type[RequestModel] | None = None,
        prefix: str | None = None,
        exclude_routes: Union[
            set[routesType],
            list[routesType],
        ] = set(),
        tags: List[str | Enum] | None = None,
        name: str = "",
        except_cols: List[str] | None = None,
        allowed_cols: List[str] | None = None,
        dependencies=[],
        *,  # 키워드 전용 인자
        # CRUDService 자동 생성을 위한 옵션들
        deleted_column: Optional[str] = None,
        relationship_key_fields: Dict[str, Set[str]] = dict(),
        relationship_exclude_fields: Dict[str, Set[str]] = dict(),
        relationship_deleted_columns: Dict[str, str] = dict(),
        allow_restore: bool = False,
        **kwargs,
    ):
        """
        Args:
            ModelType (Type[T]): 데이터 모델 클래스
            service: 서비스 클래스
        """
        self.path = f"Current file: {os.path.abspath(__file__)}"
        self.name = name
        self.ModelType = ModelType
        self.prefix = f"/{self.ModelType.__name__}" if prefix == None else prefix
        tags = [self.ModelType.__name__] if tags == None else tags
        self._router = APIRouter(
            prefix=self.prefix, tags=tags, dependencies=dependencies
        )

        self.response_model = response_model if response_model else None
        self.request_model = request_model if request_model else None

        # 서비스 주입: 외부에서 제공된 서비스가 있으면 사용, 없으면 기본 CRUDService 생성
        if service is not None:
            if callable(service):
                self.service = service()
            else:
                self.service = service
        else:
            # CRUDService 자동 생성 시 모든 관련 옵션들 전달
            self.service = CRUDService[ModelType, RequestModel, ResponseModel](
                ModelType,
                request_model=self.request_model,
                response_model=self.response_model,
                deleted_column=deleted_column,
                relationship_key_fields=relationship_key_fields,
                relationship_exclude_fields=relationship_exclude_fields,
                relationship_deleted_columns=relationship_deleted_columns,
                state_machine_validate=state_machine_validate,
            )
        if not isinstance(self.service, ServiceProtocol):
            raise ValueError("service must be a ServiceProtocol")

        self.is_soft_delete = (
            hasattr(self.service, "deleted_column")
            and getattr(self.service, "deleted_column") is not None
        )

        exclude_routes = set(map(lambda x: x.upper(), exclude_routes))  # type: ignore
        # 기본 CRUD 라우트 등록
        self.router.__module__ = self.__module__
        self.except_cols = except_cols
        self.allowed_cols = allowed_cols

        # 응답 모델이 설정된 partial 메서드 생성
        if self.response_model:
            self.get = partial(
                self._router.get, response_model=List[self.response_model]
            )
            self.post = partial(self._router.post, response_model=self.response_model)
            self.put = partial(self._router.put, response_model=self.response_model)
            self.patch = partial(self._router.patch, response_model=self.response_model)
            self.delete = partial(
                self._router.delete, response_model=self.response_model
            )
        else:
            # response_model이 None인 경우 기본 라우터 메서드 사용
            self.get = self._router.get
            self.post = self._router.post
            self.put = self._router.put
            self.patch = self._router.patch
            self.delete = self._router.delete

        # 기본 라우트 등록
        if "GET" not in exclude_routes:
            self.default_get = self._register_get_route()
            self.default_get_by_idx = self._register_get_by_idx_route()
            if hasattr(self.service, "state_machine_validate"):
                for (
                    key,
                    item,
                ) in (
                    self.service.state_machine_validate.items()  # pyright: ignore[reportAttributeAccessIssue]
                ):  # pyright: ignore[reportAttributeAccessIssue]
                    self._create_state_machine_route(key, item)
            else:
                pass
        if "POST" not in exclude_routes:
            self.default_post = self._register_post_route()
        if "PUT" not in exclude_routes:
            self.default_put = self._register_put_route()
        # if "PATCH" not in exclude_routes:
        #     self.default_patch = self._register_patch_route()
        if "DELETE" not in exclude_routes:
            self.default_delete = self._register_delete_route()
            if allow_restore:
                assert (
                    hasattr(self.service, "restore") and isinstance(getattr(self.service, "restore"), Callable)
                ), "restore 함수가 구현돼있지 않습니다. service에 restore 함수를 구현해주세요."
                self.default_restore = self._register_restore_route()

    # 타입 힌팅을 위한 헬퍼 메서드
    def get_model_type(self) -> Type[ModelType]:
        """ModelType 반환 - 타입 힌팅 보조용"""
        return self.ModelType

    def generate_api_docs(self):
        """API 문서화에 사용할 문자열을 생성합니다."""
        # 모델 필드 정보 가져오기
        fields_info = []
        for field_name, field_info in self.ModelType.model_fields.items():
            fields_info.append(f"- **{field_name}**: {field_info}")

        # 필드 정보 문자열 생성
        fields_str = "\n".join(fields_info)

        # 필터 옵션 정보
        filter_mode = (
            "화이트리스트"
            if hasattr(self, "allowed_cols") and self.allowed_cols
            else (
                "블랙리스트"
                if hasattr(self, "except_cols") and self.except_cols
                else "제한 없음"
            )
        )

        filter_info = f"- **필터 방식**: {filter_mode}"
        if hasattr(self, "allowed_cols") and self.allowed_cols:
            filter_info += f"\n- **허용된 필드**: {', '.join(self.allowed_cols)}"
        if hasattr(self, "except_cols") and self.except_cols:
            filter_info += f"\n- **제외된 필드**: {', '.join(self.except_cols)}"

        # 최종 문서 문자열
        docs = f"""

```
"""
        return docs

    def _register_get_route(self):
        response_model = self.response_model or self.ModelType

        @self._router.get("", response_model=StandardResponse[Sequence[response_model]])
        async def get(
            session: SessionDep,
            filter_json: str | None = Query(None),
            load_deleted: Optional[bool] = Query(
                default=False,
                description="Soft delete된 항목 포함 여부 (soft delete 활성화 시에만 사용)",
            ),
            User: UserOut = Depends(auth_get_current_user),
        ) -> StandardResponse[Sequence[ResponseModel]]:
            return self.service.get_standard_response(
                session, User, request_json=filter_json, load_deleted=load_deleted if load_deleted is not None else False
            )

        get.__doc__ = """
        GET: 데이터를 조회합니다.
        """
        return get

    def _register_get_by_idx_route(self):
        response_model = self.response_model or self.ModelType

        @self._router.get("/by_idx/{idx}", response_model=response_model)
        async def get_by_idx(
            session: SessionDep,
            idx: int,
            User: UserOut = Depends(auth_get_current_user),
            load_deleted: Optional[bool] = Query(
                default=False,
                description="Soft delete된 항목 포함 여부 (soft delete 활성화 시에만 사용)",
            ),
        ) -> Type[ResponseModel]:
            return cast(
                Type[ResponseModel],
                self.service.get_by_idx(
                    session,
                    User,
                    idx,
                    load_deleted=load_deleted if load_deleted is not None else False,
                ),
            )

        get_by_idx.__doc__ = """
        idx를 통해 데이터를 조회합니다.
        """
        return get_by_idx

    def _register_post_route(self):

        request_model = self.request_model or self.ModelType
        response_model = self.response_model or self.ModelType

        @self._router.post("", response_model=response_model)
        async def post(session: SessionDep, item: request_model, User: UserOut = Depends(auth_get_current_user)) -> ModelType:  # type: ignore
            return cast(
                ModelType, self.service.post(session=session, item=item, User=User)
            )

        return post

    def _register_put_route(self):
        """PUT: 전체 리소스 대체"""
        request_model = self.request_model or self.ModelType
        response_model = self.response_model or self.ModelType

        @self.router.put("/put/{idx}", response_model=response_model)
        async def put(
            session: SessionDep, idx: int, item: request_model, User=Depends(auth_get_current_user)  # type: ignore
        ) -> ModelType:
            return cast(
                ModelType,
                self.service.put(session=session, idx=idx, item=item, User=User),
            )

        return put

    # def _register_patch_route(self):
    #     """PATCH: 부분 수정 (추후 구현)"""
    #     request_model = self.request_model or self.ModelType
    #     response_model = self.response_model or self.ModelType

    #     @self._router.patch("/patch/{idx}", response_model=response_model)
    #     async def patch(
    #         session: SessionDep, idx: int, item: request_model, User=Depends(auth_get_current_user)  # type: ignore
    #     ) -> ModelType:
    #         # 현재는 PUT과 동일하게 동작 (추후 부분 수정 로직 구현 필요)
    #         return cast(
    #             ModelType,
    #             self.service.put(session=session, idx=idx, item=item, User=User),
    #         )

    #     return patch

    def _register_delete_route(self):
        model = self.ModelType
        response_model = self.response_model or self.ModelType

        @self._router.delete("/delete/{idx}", response_model=response_model)
        async def delete(
            session: SessionDep,
            idx: int,
            User=Depends(auth_get_current_user),
        ) -> ModelType:
            return cast(
                ModelType,
                self.service.delete(
                    session=session,
                    idx=idx,
                    User=User,
                ),
            )

        return delete

    def _register_restore_route(self):
        model = self.ModelType
        response_model = self.response_model or self.ModelType
        assert (
            getattr(self.service, "restore") is not None
        ), "restore method is not implemented"

        @self._router.patch("/restore/{idx}", response_model=response_model)
        async def restore(
            session: SessionDep,
            idx: int,
            User=Depends(auth_get_current_user),
        ) -> ModelType:
            return cast(
                ModelType,
                self.service.restore(  # pyright: ignore[reportAttributeAccessIssue]
                    session=session,
                    idx=idx,
                    User=User,
                ),
            )

        return restore


    def _create_state_machine_route(
        self, key: str, state_machine: StateMachine
    ) -> None:
        """
        State machine별 라우트 핸들러 생성 (클로저 문제 해결)

        Args:
            key: state_machine_validate의 키 (예: "status", "order_status")
            machine: StateMachine 인스턴스
        """
        # states 리스트에서 첫 번째 상태의 타입을 사용 (모두 같은 Enum 타입이므로)
        if not state_machine.states:
            return

        state_enum_type = type(state_machine.states[0])
        column_name = f"{key}"
        states = state_machine.states
        order = state_machine.ORDER

        # 팩토리 함수로 클로저 문제 해결
        def create_handler(_machine: StateMachine, _enum_type: Type):
            @self._router.get(
                f"/{column_name}/state_machine_info",
                response_model=StateMachineResponse,
                name=f"get_{column_name}_state_machine_info",
            )
            async def get_state_machine_handler(
                status: Optional[
                    state_enum_type  # pyright: ignore[reportInvalidTypeForm]
                ] = Query(  # pyright: ignore[reportInvalidTypeForm]
                    None
                ),  # pyright: ignore[reportInvalidTypeForm]
            ):
                """현재 상태에서 전이 가능한 다음 상태들을 반환"""
                return StateMachineResponse(
                    column_name=column_name,
                    states=states,
                    transitable_states=state_machine.get_next_allowed_states(status),
                    order=order,
                )

            return get_state_machine_handler

        create_handler(state_machine, state_enum_type)

    @property
    def router(self) -> APIRouter:
        """라우터 객체 반환"""
        return self._router


# 타입 힌팅 확장 함수
def get_model_type_from_router(
    router: CRUDRouter[ModelType, RequestModel, ResponseModel],
) -> Type[ModelType]:
    """라우터에서 모델 타입을 추출하는 헬퍼 함수"""
    return router.ModelType


# 사용 예시: 이 함수를 사용하여 명시적으로 타입을 가져올 수 있습니다
def get_typed_result(
    router: CRUDRouter[ModelType, RequestModel, ResponseModel], results: Sequence[Any]
) -> Sequence[ModelType]:
    """명시적 타입 변환 헬퍼 함수"""
    return results
