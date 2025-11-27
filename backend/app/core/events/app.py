"""
완전한 PostgreSQL 통합 Application
"""

from dataclasses import dataclass
from typing import Dict, Any, Optional, Union
from core.events.mapper import PYDANTIC_MAPPER_TOPIC

from eventsourcing.persistence import Recording
from eventsourcing.utils import get_topic

from eventsourcing_sqlalchemy.datastore import SQLAlchemyDatastore
from eventsourcing_sqlalchemy.recorders import SQLAlchemyProcessRecorder
from sqlalchemy import Table, select
from sqlmodel import Session
from core import logger
from core.events.custom_recorder import ManagedSessionRecorder
from eventsourcing.system import ProcessApplication
from eventsourcing.domain import (
    DomainEventProtocol,
    MutableOrImmutableAggregate,
    TAggregateID,
)
from eventsourcing_sqlalchemy.models import (
    NotificationTrackingRecord,
    StoredEventRecord,
)
from typing import Any, Callable, Optional, cast
from uuid import UUID, uuid4
from datetime import datetime
import psycopg
import dotenv
from dotenv import load_dotenv


# log_config.py의 설정을 사용하여 로깅 설정
class ApplicationMeta(type(ProcessApplication)):  # ProcessApplication의 메타클래스 상속
    _instances = []
    _classes = {}
    # 모든 서브클래스를 저장할 클래스 변수
    _subclasses = []

    # 현재는 start_up.py에서 hash변경 시 실행중
    def __new__(mcs, name, bases, namespace):
        cls = super().__new__(mcs, name, bases, namespace)

        # SessionApplication의 서브클래스인지 체크
        if any(isinstance(base, ApplicationMeta) for base in bases):
            # SessionApplication 자체는 제외
            if name != "SessionApplication":
                ApplicationMeta._subclasses.append(cls)
                # logger.info(f"Registered: {name}")
                ApplicationMeta._classes[name] = cls
        return cls

    @classmethod
    def event_model_definition(cls):
        result = ""
        super_definition = f"""
#auto generated for alembic
#generated from events/app.py
from typing import Optional
from sqlmodel import Field
from eventsourcing_sqlalchemy.models import StoredEventRecord, NotificationTrackingRecord
from sqlalchemy import Index

class stored_events(StoredEventRecord):
    __abstract__ = True



class notification_tracking(NotificationTrackingRecord):
    __abstract__ = True

"""

        result += super_definition
        for key, value in cls._classes.items():
            result += f"""
            
class {key.lower()}_events(stored_events):
    __tablename__ = "{key.lower()}_events"
    __table_args__ = (
        Index(
            "{key.lower()}_aggregate_event_index",
            "originator_id",
            "originator_version",
            unique=True,
        ),
        {{'extend_existing': True}},
    )
class {key.lower()}_tracking(notification_tracking):
    __tablename__ = "{key.lower()}_tracking"
    __table_args__ = ({{'extend_existing': True}},)
            """
        return result

    @classmethod
    def write_event_model(cls):
        result = cls.event_model_definition()
        with open("models/EventModels.py", "w") as f:
            f.write(result)


class SessionApplication(ProcessApplication, metaclass=ApplicationMeta):
    # """
    # 세션 기반의 이벤트소싱 애플리케이션 클래스

    # 각 세션마다 고유한 어댑터 클래스를 동적으로 생성하여 세션 관리를 수행합니다.
    # 이벤트 저장소와 트래킹을 위한 테이블 구조를 런타임에 정의하고 관리합니다.

    # 주요 기능:
    #     - 세션별 고유 어댑터 클래스 동적 생성 및 관리
    #     - 이벤트 저장소 테이블 구조 정의 및 접근
    #     - 이벤트 트래킹 테이블 구조 정의 및 접근

    # Attributes:
    #     session: SQLAlchemy 세션 객체
    #     event_table_cls: 이벤트 저장을 위한 테이블 클래스
    #     event_table_name: 이벤트 테이블명
    #     event_table: 이벤트 테이블 객체
    #     tracking_table_name: 트래킹 테이블명
    #     tracking_record_cls: 트래킹 레코드 클래스
    #     tracking_table: 트래킹 테이블 객체
    # """
    """
    반드시 *args, **kwargs를 받아야 합니다.
    """

    _adapter_class = {}

    @classmethod
    def get_all_subclasses(cls):
        return ApplicationMeta._subclasses

    def __init__(self, session: Session, *args, **kwargs):
        # session별로 동적으로 고유한 adapter 클래스 생성
        # 
        # 참고: scoped_session_topic을 설정하면 eventsourcing의 datastore가
        # is_scoped_session=True로 동작하여 transaction(commit=True)에서도
        # 실제 commit을 하지 않습니다.
        #
        # 하지만 ManagedSessionRecorder가 insert_events(session=...)로 
        # 명시적으로 session을 받아서 처리하므로, transaction wrapper를 우회합니다.
        # 
        # 이 설정은 주로 select_events() 등 읽기 작업에서 같은 session을
        # 재사용하기 위해 유지합니다.
        session_id = id(session)
        if session_id not in self.__class__._adapter_class:
            adapter_class_name = f"SessionAdapter_{session_id}"

            # 동적으로 클래스 생성 (한 번만)
            def __getattribute__(self, item: str) -> None:
                return getattr(session, item)

            self.__class__._adapter_class[session_id] = type(
                adapter_class_name,
                (),
                {
                    "__getattribute__": __getattribute__,
                },
            )
            # 생성된 클래스의 인스턴스 생성
        scoped_session_topic = get_topic(self.__class__._adapter_class[session_id])

        env = kwargs.get("env", {})
        kwargs.pop("env", None)
        if not env:
            env = {}
        env["SQLALCHEMY_SCOPED_SESSION_TOPIC"] = scoped_session_topic
        env["MAPPER_TOPIC"] = PYDANTIC_MAPPER_TOPIC

        super().__init__(
            env=env,
        )

        # 기존 recorder를 ManagedSessionRecorder로 교체
        old_recorder = cast(SQLAlchemyProcessRecorder, self.recorder)
        self.recorder = ManagedSessionRecorder(
            datastore=old_recorder.datastore,
            events_table_name=old_recorder.events_table_name,
            tracking_table_name=old_recorder.tracking_table_name,
            schema_name=old_recorder.schema_name if hasattr(old_recorder, 'schema_name') else None,
        )
        self.recorder.datastore = cast(SQLAlchemyDatastore, self.recorder.datastore)
        
        # ✅ Repository도 새로운 recorder를 사용하도록 재생성
        from eventsourcing.persistence import EventStore, AggregateRecorder
        self.events = EventStore(
            mapper=self.mapper,
            recorder=cast(AggregateRecorder, self.recorder),
        )
        self.repository.event_store = self.events
        self.event_table_cls = cast(StoredEventRecord, self.recorder.events_record_cls)
        self.event_table_name = self.recorder.events_table_name
        self.event_table = cast(
            Table, self.event_table_cls.__table__  # pyright: ignore[reportAttributeAccessIssue]
        )  # pyright: ignore[reportAttributeAccessIssue]

        self.datastore = self.recorder.datastore
        self.tracking_table_name = self.recorder.tracking_table_name
        self.tracking_record_cls = cast(
            NotificationTrackingRecord, self.recorder.tracking_record_cls 
        )
        self.tracking_table = cast(
            Table, self.tracking_record_cls.__table__  # pyright: ignore[reportAttributeAccessIssue]
        )  # pyright: ignore[reportAttributeAccessIssue]

        # self.session의 경우 약한 참조를 유지
        self.session = session

    def get_all_originator_ids(self):

        return list(
            map(
                lambda x: x[0],
                self.session.exec(select(self.event_table_cls.originator_id))  # pyright: ignore[reportArgumentType, reportCallIssue]
                .unique()
                .all(),
            )
        )

    def get_events(
        self,
        ids: list[UUID],
    ):
        events = []
        for id in ids:
            events.append(
                self.repository.get(
                    id,
                )
            )
        return events

    def query_states(
        self, offset: int = 0, limit: Union[int, str] = 100, isexact: bool = False, **kwargs: Any
    ):
        """상태별 쿼리 - 조건 필터링"""
        originator_ids = self.get_all_originator_ids()
        
        # limit이 "all"인 경우 전체 개수로 설정
        if limit == "all":
            actual_limit = len(originator_ids)
        else:
            actual_limit = int(limit)
        
        filtered_events = []
        processed_count = 0

        for id in originator_ids:
            try:
                event = self.repository.get(id)
                if event and self._matches_query_filters(
                    event, kwargs, isexact=isexact
                ):
                    # offset 처리
                    if processed_count < offset:
                        processed_count += 1
                        continue

                    filtered_events.append(event)

                    # limit 처리 (전체 조회가 아닌 경우만)
                    if limit != "all" and len(filtered_events) >= actual_limit:
                        break

            except ValueError:
                # 필터 조건 오류는 전파
                raise
            except Exception:
                # 이벤트를 읽을 수 없는 경우만 건너뛰기
                continue

        return filtered_events

    def _matches_query_filters(
        self, event, filters: Dict[str, Any], isexact: bool = False
    ) -> bool:
        """간단한 쿼리 필터 조건 확인 - contains 패턴"""
        for key, expected_value in filters.items():
            # event에 해당 속성이 없으면 에러 발생 (휴먼 에러 방지)
            if not hasattr(event, key):
                raise ValueError(
                    f"이벤트에 '{key}' 속성이 존재하지 않습니다. 사용 가능한 속성: {list(event.__dict__.keys())}"
                )

            # 속성 값 가져오기
            event_value = getattr(event, key)

            # 문자열 포함 여부 검사 (contains 패턴)
            if isinstance(event_value, str) and isinstance(expected_value, str):
                if isexact:
                    if expected_value != event_value:
                        return False
                else:
                    if expected_value.lower() not in event_value.lower():
                        return False

            else:
                # 문자열이 아닌 경우 정확히 일치하는지 검사
                if event_value != expected_value:
                    return False

        return True

    def save(
        self,
        *objs: MutableOrImmutableAggregate[TAggregateID]
        | DomainEventProtocol[TAggregateID]
        | None,
        **kwargs: Any,
    ) -> list[Recording[Any]]:
        # ManagedSessionRecorder에 session을 전달하기 위해
        # saved_kwargs에 session 추가
        kwargs['session'] = self.session
        return super().save(*objs, **kwargs)
