from typing import Dict, Sequence, TypeVar, Protocol, runtime_checkable, Optional
from sqlmodel import SQLModel
from api.user.schemas import UserOut
from core.base.CRUD.crud_types import RequestModel, ResponseModel
from core.base.CRUD.schemas import StandardResponse
from core.database import Session
from core.base.model import Base
from core.internal.sort import ModelType
from core.state_machine.schema import StateMachineSchema

@runtime_checkable
class ServiceProtocol(Protocol[ModelType, RequestModel, ResponseModel]):
    """CRUD 작업을 위한 서비스 인터페이스 프로토콜"""

    def post(self, session: Session, item: RequestModel, User: UserOut) -> ResponseModel:
        """새 항목 생성"""
        ...

    def put(self, session: Session, idx: int, item: RequestModel, User: UserOut) -> ResponseModel:
        """항목 전체 업데이트"""
        ...

    def delete(
        self,
        session: Session,
        idx: int,
        User: UserOut,
    ) -> ResponseModel:
        """항목 삭제"""
        ...

    def get_by_idx(
        self, 
        session: Session, 
        User: UserOut, 
        idx: int, 
        load_deleted: bool = False
    ) -> ResponseModel:
        """idx로 단일 항목 조회"""
        ...
    # def get_count(
    #     self,
    #     session: Session,
    #     request_json: Optional[str] = None,
    # ) -> int:
    #     """항목 개수 조회"""
    #     ...
    def get_standard_response(
        self,
        session: Session,
        User: UserOut,
        request_json: Optional[str] = None,
        load_deleted: bool = False,
    ) -> StandardResponse[Sequence[ResponseModel]]: 
        """표준 응답 형식으로 데이터 조회"""
        ...
