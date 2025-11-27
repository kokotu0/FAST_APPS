"""
EventMediator - 중재자 패턴 기반 이벤트 시스템의 핵심 클래스

EventMediator: 모든 서비스 간 통신을 중재하는 단일 중재자
- 요청 스코프별 싱글톤 패턴
- 자동 서비스 등록
- Pipeline 기반 이벤트 전파 제어
"""

from typing import Any, Callable, Dict, List, Optional, Type, TypeVar
from contextlib import contextmanager
from threading import Lock
import logging
import inspect

from sqlmodel import Session
from api.user.schemas import UserOut

from .Pipe import Pipes

T = TypeVar('T')
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class EventMediator:
    """
    중재자 패턴 - 모든 서비스의 이벤트 통신을 중재
    
    하나의 EventMediator가 모든 App 인스턴스를 관리하고
    이벤트를 중재함
    
    요청 스코프별 싱글톤: __new__를 사용해 같은 세션은 같은 인스턴스 반환
    
    사용법:
        # 단순하게 생성자 호출!
        mediator = EventMediator(session, current_user, pipes=Pipes([...]))
    """
    
    _request_scope_mediators: Dict[int, 'EventMediator'] = {}
    _lock: Lock = Lock()
    
    # 인스턴스 변수 타입 힌팅
    _initialized: bool
    _pipes: Optional[Pipes]
    session: Session
    current_user: UserOut
    request_id: int
    _event_handlers: Dict[str, List[Callable]]
    _apps: Dict[str, Any]
    _pipeline_graph: Dict[str, List[str]]  # Pipeline 그래프 (App → 다음 App들)

    
    def __new__(cls, session: Session, current_user: UserOut, pipes: Optional[Pipes] = None):
        """
        싱글톤 패턴 구현 - 같은 세션(요청)에서는 기존 인스턴스 반환
        """
        request_id = id(session)
        
        with cls._lock:
            if request_id in cls._request_scope_mediators:
                logger.debug(f"Reusing EventMediator for request {request_id}")
                return cls._request_scope_mediators[request_id]
            
            # 새 인스턴스 생성
            instance = super().__new__(cls)
            cls._request_scope_mediators[request_id] = instance
            
            # 초기화 플래그 (__init__이 여러 번 호출되는 것 방지)
            instance._initialized = False
            instance._pipes = pipes  # Pipes를 임시 저장
            
            logger.debug(f"Created new EventMediator for request {request_id}")
            return instance
    
    def __init__(self, session: Session, current_user: UserOut, pipes: Optional[Pipes] = None):
        """
        EventMediator 초기화
        
        Args:
            session: DB 세션 (필수)
            current_user: 현재 사용자 (필수)
            pipes: 명시적 Pipeline 선언 (옵션)
        """
        # 이미 초기화되었으면 스킵 (싱글톤이므로 __init__이 여러 번 호출될 수 있음)
        if self._initialized:
            logger.debug(f"Already initialized, registered apps: {list(self._apps.keys())}")
            return
        
        self.session = session
        self.current_user = current_user
        self.request_id = id(session)
        self._event_handlers = {}
        self._apps = {}
        self._pipeline_graph = {}  # Pipeline 그래프 초기화
        
        # 호출한 Service 클래스 이름 자동 감지
        self.service_name = self._detect_caller_service()
        
        logger.debug(f"EventMediator initialized (request_id={self.request_id}, service={self.service_name})")
        
        # Pipes가 제공되면 자동으로 모든 App 등록
        if pipes:
            logger.debug(f"Setting up {pipes}")
            try:
                all_apps = pipes.instantiate_all(session, current_user)
                logger.debug(f"Instantiated {len(all_apps)} app(s): {[app.__class__.__name__ for app in all_apps]}")
                
                for app in all_apps:
                    self.register_app(app)
                
                logger.debug(f"Registered apps: {list(self._apps.keys())}")
                
                # Pipeline 그래프 생성 (순방향 전파만 허용)
                self._build_pipeline_graph(pipes)
                
            except Exception as e:
                logger.error(f"Failed to instantiate apps: {e}", exc_info=True)
                raise
            
            # Pipeline 정보는 이미 메타클래스에서 등록됨
        
        self._initialized = True
    
    def _build_pipeline_graph(self, pipes: Pipes):
        """
        Pipeline 그래프 구축 (바로 다음 단계만 전파)
        
        예: Pipeline([A, B, C])
        -> A can propagate to B only
        -> B can propagate to C only
        -> C cannot propagate to anyone
        """
        for pipeline in pipes.pipelines:
            app_names = [cls.__name__ for cls in pipeline.app_classes]
            
            for i, app_name in enumerate(app_names):
                if app_name not in self._pipeline_graph:
                    self._pipeline_graph[app_name] = []
                
                # 바로 다음 단계만 추가 (i + 1)
                if i + 1 < len(app_names):
                    next_app = app_names[i + 1]
                    if next_app not in self._pipeline_graph[app_name]:
                        self._pipeline_graph[app_name].append(next_app)
        
        logger.debug(f"Pipeline Graph: {self._pipeline_graph}")
    
    def _is_allowed_propagation(self, source_app_name: str, target_app_name: str) -> bool:
        """
        이벤트 전파가 허용되는지 확인
        
        Pipeline 구조에서:
        - 바로 다음 단계로만 전파 허용
        - Pipeline 외부 구독자 차단
        
        Args:
            source_app_name: 이벤트를 발행한 App
            target_app_name: 이벤트를 구독하려는 App
            
        Returns:
            True: 전파 허용 (바로 다음 단계)
            False: 전파 차단 (역방향, 건너뛰기, 외부)
        """
        # Pipeline 그래프가 없으면 모든 전파 허용 (기본 동작)
        if not self._pipeline_graph:
            return False
        
        # source_app이 Pipeline에 없으면 차단
        if source_app_name not in self._pipeline_graph:
            logger.debug(
                f"Source app not in pipeline: {source_app_name}"
            )
            return False
        
        # target_app이 Pipeline에 없으면 차단 (외부 구독자 불가)
        if target_app_name not in self._pipeline_graph:
            logger.debug(
                f"Target app not in pipeline: {target_app_name}"
            )
            return False
        
        # source → target이 바로 다음 단계인지 확인
        allowed_targets = self._pipeline_graph.get(source_app_name, [])
        is_next_step = target_app_name in allowed_targets
        
        if not is_next_step:
            logger.debug(
                f"Not next step: {source_app_name} -> {target_app_name} "
                f"(allowed: {allowed_targets})"
            )
        
        return is_next_step
    
    @staticmethod
    def _detect_caller_service() -> str:
        """
        호출 스택을 분석하여 Service 클래스 이름 자동 감지
        
        Returns:
            Service 클래스 이름 (예: "BuyService", "SalesService")
        """
        try:
            # 호출 스택 확인 (현재 프레임부터 거슬러 올라감)
            frame = inspect.currentframe()
            if frame is None:
                return "Unknown"
            
            # __init__ -> __new__ -> Service.__init__ 순서로 올라감
            # 3-4단계 위에 Service 클래스가 있을 것
            for _ in range(10):  # 최대 10 프레임까지 확인
                frame = frame.f_back
                if frame is None:
                    break
                
                # 프레임의 locals에서 'self' 찾기
                local_self = frame.f_locals.get('self')
                if local_self is not None:
                    class_name = local_self.__class__.__name__
                    # Service, System 등으로 끝나는 클래스 찾기
                    if class_name.endswith('Service') or class_name.endswith('System'):
                        return class_name
            
            return "Unknown"
        except Exception as e:
            logger.warning(f"Failed to detect caller service: {e}")
            return "Unknown"
    
    @classmethod
    def cleanup_request(cls, request_id: int):
        """요청 완료 후 Mediator 정리"""
        with cls._lock:
            if request_id in cls._request_scope_mediators:
                del cls._request_scope_mediators[request_id]
                logger.debug(f"Cleaned up EventMediator for request {request_id}")
    

    
    def register_app(self, app_instance: Any, app_name: Optional[str] = None):
        """
        App 등록 (중복 방지)
        
        Args:
            app_instance: App 인스턴스 (EventMixin 상속)
            app_name: App 이름 (없으면 클래스명 사용)
        """
        name = app_name if app_name is not None else app_instance.__class__.__name__
        
        # 이미 등록된 App이면 스킵 (중복 방지)
        if name in self._apps:
            logger.debug(f"Already registered: {name}")
            return
        
        self._apps[name] = app_instance
        
        # EventMediator를 app에 주입
        app_instance.mediator = self
        
        # 데코레이터로 마킹된 메서드들을 찾아서 등록
        for attr_name in dir(app_instance):
            if attr_name.startswith('_'):
                continue
                
            attr = getattr(app_instance, attr_name)
            
            # @event_subscriber로 마킹된 메서드 등록
            if hasattr(attr, '_event_subscriptions'):
                for event_name in attr._event_subscriptions:
                    if event_name not in self._event_handlers:
                        self._event_handlers[event_name] = []
                    self._event_handlers[event_name].append(attr)
                    logger.debug(f"[{name}.{attr_name}] subscribed to: {event_name}")
        
        logger.debug(f"Registered: {name}")
    
    def publish(self, event_name: str, source_app_name: Optional[str] = None, **kwargs):
        """
        이벤트 발행 (Pipeline 순차 전파만 허용)
        
        등록된 핸들러 중 Pipeline 구조상 바로 다음 단계에만 전파
        
        Args:
            event_name: 이벤트 이름
            source_app_name: 이벤트를 발행한 App 이름 (자동 추적)
            **kwargs: 이벤트 데이터
        """
        logger.debug(f"Event: {event_name}")
        
        if event_name not in self._event_handlers:
            return []
        
        results = []
        handlers = self._event_handlers[event_name]
        
        for handler in handlers:
            try:
                # 핸들러가 속한 App 찾기
                target_app = None
                target_app_name = None
                
                for app_name, app_instance in self._apps.items():
                    if hasattr(app_instance, handler.__name__):
                        method = getattr(app_instance, handler.__name__)
                        if method == handler:
                            target_app = app_instance
                            target_app_name = app_name
                            break
                
                # Pipeline 순차 전파 체크 (바로 다음 단계만)
                if source_app_name and target_app_name:
                    if not self._is_allowed_propagation(source_app_name, target_app_name):
                        continue
                
                result = handler(**kwargs)
                
                if result is not None:
                    results.append(result)
                    
            except Exception as e:
                logger.error(f"Error in {handler.__name__}: {e}", exc_info=True)
                raise e
        
        return results
    
    def get_app(self, app_class: Type[T]) -> T:
        """
        등록된 App 인스턴스 가져오기
        
        Returns:
            App 인스턴스 (타입 힌팅 자동!)
        """
        app_name = app_class.__name__
        if app_name not in self._apps:
            registered_apps = list(self._apps.keys())
            error_msg = (
                f"App '{app_name}' not registered in EventMediator.\n"
                f"   Registered apps: {registered_apps}\n"
                f"   Service: {self.service_name}\n"
                f"   Request ID: {self.request_id}\n"
                f"   Initialized: {self._initialized}\n"
                f"   Pipes: {self._pipes}"
            )
            logger.error(error_msg)
            raise ValueError(f"App '{app_name}' not registered in EventMediator. Registered: {registered_apps}")
        return self._apps[app_name]
    
    def get_pipeline_info(self) -> Dict[str, Any]:
        """
        현재 EventMediator의 상세 정보 반환
        
        Returns:
            {
                "apps": ["AppName1", "AppName2", ...],
                "event_handlers": {...},
                "publishers": {...},
                "subscribers": {...},
                "pipelines": [...],
                "pipeline_graph": {...},
                "request_id": int
            }
        """
        # 1. 등록된 App 목록
        apps_list = list(self._apps.keys())
        
        # 2. 이벤트 핸들러 매핑
        event_handlers_info = {}
        for event_name, handlers in self._event_handlers.items():
            handler_names = []
            for handler in handlers:
                # 핸들러가 속한 App 찾기
                for app_name, app_instance in self._apps.items():
                    if hasattr(app_instance, handler.__name__):
                        handler_names.append(f"{app_name}.{handler.__name__}")
                        break
            event_handlers_info[event_name] = handler_names
        
        # 3. Publisher 정보 (어떤 메서드가 어떤 이벤트를 발행하는지)
        publishers_info = {}
        for app_name, app_instance in self._apps.items():
            publishers = []
            for attr_name in dir(app_instance):
                if attr_name.startswith('_'):
                    continue
                attr = getattr(app_instance, attr_name)
                if hasattr(attr, '_is_event_publisher') and attr._is_event_publisher:
                    publishers.append({
                        "method": attr_name,
                        "event": attr._event_name,
                    })
            if publishers:
                publishers_info[app_name] = publishers
        
        # 4. Subscriber 정보 (어떤 메서드가 어떤 이벤트를 구독하는지)
        subscribers_info = {}
        for app_name, app_instance in self._apps.items():
            subscribers = []
            for attr_name in dir(app_instance):
                if attr_name.startswith('_'):
                    continue
                attr = getattr(app_instance, attr_name)
                if hasattr(attr, '_event_subscriptions'):
                    for event_name in attr._event_subscriptions:
                        subscribers.append({
                            "method": attr_name,
                            "event": event_name,
                        })
            if subscribers:
                subscribers_info[app_name] = subscribers
        
        # 5. Pipeline 구조 (Pipes가 있는 경우)
        pipelines_info = []
        if self._pipes:
            for i, pipeline in enumerate(self._pipes.pipelines, 1):
                pipelines_info.append({
                    "pipeline_id": i,
                    "apps": [cls.__name__ for cls in pipeline.app_classes],
                    "flow": " → ".join([cls.__name__ for cls in pipeline.app_classes]),
                })
        
        return {
            "apps": apps_list,
            "event_handlers": event_handlers_info,
            "publishers": publishers_info,
            "subscribers": subscribers_info,
            "pipelines": pipelines_info,
            "pipeline_graph": self._pipeline_graph,
            "request_id": self.request_id,
        }
    
    @contextmanager
    def transaction(self):
        """트랜잭션 컨텍스트"""
        try:
            yield self
            self.session.commit()
            logger.debug("Transaction committed")
        except Exception as e:
            self.session.rollback()
            logger.error(f"Transaction rolled back: {e}")
            raise


# 하위 호환성을 위해 SimpleEventBus는 EventMediator의 별칭으로 유지
SimpleEventBus = EventMediator
