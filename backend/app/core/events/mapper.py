from dataclasses import dataclass
from eventsourcing.utils import get_topic
from sqlmodel import SQLModel
from eventsourcing.domain import Aggregate, event
from eventsourcing.persistence import Mapper, StoredEvent
from eventsourcing.domain import DomainEventProtocol
from typing import Any, cast
from pydantic import BaseModel
from eventsourcing.utils import resolve_topic
from uuid import UUID
import logging
logger = logging.getLogger(__name__)

class PydanticMapper(Mapper[UUID]):
    def to_stored_event(self, domain_event: DomainEventProtocol[UUID]) -> StoredEvent:
        topic = get_topic(domain_event.__class__)
        
        # # dataclass인 경우 asdict 사용, BaseModel인 경우 model_dump 사용
        # logger.debug(f"domain_event: {domain_event}")
        # if hasattr(domain_event, 'model_dump'):
        #     event_state = cast(BaseModel, domain_event).model_dump(mode="json")
        # elif hasattr(domain_event, '__dataclass_fields__'):
        #     from dataclasses import asdict
        #     event_state = asdict(domain_event)
        # else : 
        #     event_state = domain_event
        event_state = domain_event.__dict__.copy()
        
        # 중첩된 Pydantic 객체들을 재귀적으로 딕셔너리로 변환
        event_state = self._convert_pydantic_objects(event_state)
        stored_state = self.transcoder.encode(event_state)
        if self.compressor:
            stored_state = self.compressor.compress(stored_state)
        if self.cipher:
            stored_state = self.cipher.encrypt(stored_state)
        return StoredEvent(
            originator_id=domain_event.originator_id,
            originator_version=domain_event.originator_version,
            topic=topic,
            state=stored_state,
        )
    
    def _convert_pydantic_objects(self, obj: Any) -> Any:
        """중첩된 Pydantic 객체들을 재귀적으로 딕셔너리로 변환"""
        from enum import Enum
        
        if isinstance(obj, Enum):
            # Enum인 경우 값과 클래스 정보 저장
            return {"__enum_value__": obj.value, "__enum_class__": get_topic(obj.__class__)}
        elif isinstance(obj, type):
            # 클래스 타입인 경우 문자열로 변환
            return f"<class '{obj.__module__}.{obj.__name__}'>" 
        elif hasattr(obj, 'model_dump') and not isinstance(obj, type):
            # Pydantic 객체 인스턴스인 경우 (클래스가 아닌)
            return {**obj.model_dump(), "__pydantic_model__": get_topic(obj.__class__)}
        elif isinstance(obj, dict):
            # 딕셔너리인 경우 각 값에 대해 재귀 호출
            return {key: self._convert_pydantic_objects(value) for key, value in obj.items()}
        elif isinstance(obj, list):
            # 리스트인 경우 각 요소에 대해 재귀 호출
            return [self._convert_pydantic_objects(item) for item in obj]
        else:
            # 기본 타입인 경우 그대로 반환
            return obj
    def to_domain_event(self, stored_event: StoredEvent) -> DomainEventProtocol[UUID]:
            stored_state = stored_event.state
            if self.cipher:
                stored_state = self.cipher.decrypt(stored_state)
            if self.compressor:
                stored_state = self.compressor.decompress(stored_state)
            event_state: dict[str, Any] = self.transcoder.decode(stored_state)
            
            cls = resolve_topic(stored_event.topic)

            # Versioning
            class_version = getattr(cls, "class_version", 1)
            from_version = event_state.pop("class_version", 1)
            while from_version < class_version:
                getattr(cls, f"upcast_v{from_version}_v{from_version + 1}")(event_state)
                from_version += 1
            
            event_state = self._reconstruct_pydantic_objects(event_state)

            return cls(**event_state)
    def _reconstruct_pydantic_objects(self, obj: Any) -> Any:
        """딕셔너리를 Pydantic 모델로 재구성"""
        
        if isinstance(obj, dict):
            # Enum 복원 확인
            if "__enum_value__" in obj and "__enum_class__" in obj:
                enum_class = resolve_topic(obj["__enum_class__"])
                return enum_class(obj["__enum_value__"])
            
            # 딕셔너리인 경우 각 값에 대해 재귀 호출
            reconstructed = {key: self._reconstruct_pydantic_objects(value) for key, value in obj.items()}
            # Pydantic 모델로 재구성 시도
            if "__pydantic_model__" in reconstructed:
                topic = reconstructed.pop("__pydantic_model__")
                model_class = cast(type[BaseModel], resolve_topic(topic))
                return model_class.model_validate(reconstructed)
            else:
                return reconstructed
        elif isinstance(obj, list):
            # 리스트인 경우 각 요소에 대해 재귀 호출
            return [self._reconstruct_pydantic_objects(item) for item in obj]
        else:
            # 기본 타입인 경우 그대로 반환
            return obj
PYDANTIC_MAPPER_TOPIC = get_topic(PydanticMapper)