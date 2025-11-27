from typing import Optional, Union
import functools
import inspect
import os
import threading
from typing import Any, Callable, ClassVar, Coroutine, cast
from uuid import UUID
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlmodel import Session, select

# .env 파일 로드
from dotenv import load_dotenv

try:
    from eventsourcing.domain import TAggregateID
    from eventsourcing.projection import TApplication
    from eventsourcing.system import (
        Follower,
        Leader,
        ProcessApplication,
        RecordingEvent,
        RecordingEventReceiver,
        Runner,
        System,
        SingleThreadedRunner,
    )
    from eventsourcing.utils import EnvType, get_topic
    from eventsourcing.persistence import Mapper, Recording
    from eventsourcing_sqlalchemy.datastore import SQLAlchemyDatastore
    from eventsourcing_sqlalchemy.recorders import SQLAlchemyProcessRecorder
    EVENTSOURCING_AVAILABLE = True
except ImportError:
    EVENTSOURCING_AVAILABLE = False
    TAggregateID = Any
    TApplication = Any
    Follower = Any
    Leader = Any
    ProcessApplication = Any
    RecordingEvent = Any
    RecordingEventReceiver = Any
    Runner = Any
    System = Any
    SingleThreadedRunner = Any
    EnvType = Any
    Mapper = Any
    Recording = Any

from api.user.schemas import UserOut
from core.database import get_session
from core.events.app import SessionApplication
import logging
logger = logging.getLogger(__name__)

load_dotenv()

# PostgreSQL 데이터베이스 설정


class Pipeline:
    def __init__(
        self, pipeline: list[type[SessionApplication]], title: Optional[str] = None
    ):
        self.pipes = pipeline
        self.title = title or self._generate_title()

    def _generate_title(self) -> str:
        """파이프라인 제목 자동 생성"""
        app_names = [app.__name__.replace("App", "") for app in self.pipes]
        return " -> ".join(app_names)

    def __str__(self):
        return f"Pipeline({self.title})"

    def __iter__(self):
        return iter(self.pipes)

    def __repr__(self):
        return self.__str__()


class Pipes:
    def __init__(self, pipeline: list[Pipeline]):
        self.pipeline = pipeline

    def __str__(self):
        return f"Pipes({self.pipeline})"

    def __repr__(self):
        return self.__str__()

    def __iter__(self):
        return iter(self.pipeline)


class SessionSingleThreadedRunner(
    Runner[TAggregateID], RecordingEventReceiver[TAggregateID]
):

    def __init__(
        self, system: System, session: Session, env: dict = {}, *args, **kwargs
    ):
        # super().__init__() 호출하지 않음!
        # 대신 Runner의 __init__만 호출 (조부모 클래스)
        Runner.__init__(self, system=system, env=env)

        # SingleThreadedRunner의 필수 속성들 직접 초기화
        self.apps = {}
        self._recording_events_received = []
        self._prompted_names_lock = threading.Lock()
        self._prompted_names = set()
        self._processing_lock = threading.Lock()

        # session 저장
        self.session = session

        # session과 함께 apps 생성 (한 번만!)
        # Construct followers
        for name in self.system.followers:
            self.apps[name] = self.system.follower_cls(name)(
                session=self.session, env=self.env, *args, **kwargs
            )

        # Construct leaders
        for name in self.system.leaders_only:
            self.apps[name] = self.system.leader_cls(name)(
                session=self.session, env=self.env, *args, **kwargs
            )

        # Construct singles
        for name in self.system.singles:
            self.apps[name] = self.system.get_app_cls(name)(
                session=self.session, env=self.env, *args, **kwargs
            )

    def start(self) -> None:
        """Starts the runner. The applications mentioned in the system definition
        are constructed. The followers are set up to follow the applications
        they are defined as following in the system definition. And the leaders
        are set up to lead the runner itself.
        """
        super().start()

        # Setup followers to follow leaders.
        for edge in self.system.edges:
            leader_name = edge[0]
            follower_name = edge[1]
            leader = cast("Leader[Any]", self.apps[leader_name])
            follower = cast(Follower[Any], self.apps[follower_name])
            assert isinstance(leader, Leader)
            assert isinstance(follower, Follower)
            follower.follow(leader_name, leader.notification_log)

        # Setup leaders to lead this runner.
        for name in self.system.leaders:
            leader = cast("Leader[Any]", self.apps[name])
            assert isinstance(leader, Leader)
            leader.lead(self)

    def receive_recording_event(
        self, new_recording_event: RecordingEvent[TAggregateID]
    ) -> None:
        """Receives recording event by appending the name of the leader
        to a list of prompted names.

        Then, unless this method has previously been called and not yet returned,
        each of the prompted names is resolved to a leader application, and its
        followers pull and process events from that application. This may lead to
        further names being added to the list of prompted names. This process
        continues until there are no more prompted names. In this way, a system
        of applications will process all events in a single thread.
        """
        leader_name = new_recording_event.application_name
        with self._prompted_names_lock:
            self._prompted_names.add(leader_name)

        if self._processing_lock.acquire(blocking=False):
            try:
                while True:
                    with self._prompted_names_lock:
                        prompted_names = self._prompted_names
                        self._prompted_names = set()

                        if not prompted_names:
                            break

                    for leader_name in prompted_names:
                        for follower_name in self.system.leads[leader_name]:
                            follower = cast(Follower[Any], self.apps[follower_name])
                            follower.pull_and_process(leader_name)

            finally:
                self._processing_lock.release()

    def stop(self) -> None:
        for app in self.apps.values():
            app.close()
        self.apps.clear()

    def get(self, cls: type[TApplication]) -> TApplication:
        app = self.apps[cls.name]
        assert isinstance(app, cls)
        return app


class SessionSystem(System):

    def __init__(self, session: Session, current_user: UserOut, pipes: Pipes):
        super().__init__(pipes=pipes)
        self.session = session
        self.current_user = current_user
        self.pipes = pipes

    @classmethod
    def session_runner(cls, app_cls: type):
        """
        주어진 `app_cls`를 실행하기 위한 데코레이터입니다.
        이 데코레이터는 동기 및 비동기 함수 모두를 지원합니다.

        사용 예시:
        반드시 app:TestApplication 인자를 추가해야 합니다.
        @SessionSystem.session_runner(TestApplication)
        def create_test(self, app:TesstApplication,name: str):
            return app.create_test(name)
        self를 주입하면 안됩니다. 타입힌팅의 경우 #ignore처리 합시다.
        """

        def decorator(func: Callable):
            # @functools.wraps(func)
            # async def async_wrapper(self, *args, **kwargs):
            #     # SessionSystem 인스턴스 생성
            #     system = cls(
            #         session=self.session,
            #         current_user=getattr(self, "current_user", None),
            #         pipes=getattr(self, "pipes", {}),
            #     )

            #     with SessionSingleThreadedRunner(
            #         system=system,
            #         session=self.session,
            #         env={},
            #         current_user=getattr(self, "current_user", None),
            #     ) as runner:
            #         app = runner.get(app_cls)
            #         # 원래 함수에 'app' 인자를 추가하여 호출합니다.
            #         return await func(self, app, *args, **kwargs)

            @functools.wraps(func)
            def sync_wrapper(self, *args, **kwargs):
                # SessionSystem 인스턴스 생성
                system = cls(
                    session=self.session,
                    current_user=cast(UserOut, getattr(self, "current_user", None)),
                    pipes=getattr(self, "pipes", Pipes([])),
                )

                with SessionSingleThreadedRunner(
                    system=system,
                    session=self.session,
                    env={},
                    current_user=getattr(self, "current_user", None),
                ) as runner:
                    app = runner.get(app_cls)
                    return func(self, app, *args, **kwargs)

            # # 원래 함수가 비동기인지 확인하고, 적절한 래퍼를 반환합니다.
            # if inspect.iscoroutinefunction(func):
            #     return async_wrapper
            # else:
            return sync_wrapper

        return decorator
