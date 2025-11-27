# Events Module

이벤트 시스템 관련 모듈

## 📁 파일 구조

- **`app.py`** - SessionApplication (기존 eventsourcing 기반)
- **`sys.py`** - SessionSystem (기존 eventsourcing 기반)
- **`event_manager.py`** ✨ - 간단한 데코레이터 기반 이벤트 버스 (신규)
- **`command_system.py`** - MediatR 패턴 구현
- **`event_types.py`** - 이벤트 타입 정의

## 🚀 Quick Start

### Simple Event Bus 사용 (권장)

```python
from core.events.event_manager import EventMixin, event_publisher, event_subscriber

class MyService(EventMixin):
    def __init__(self, session, current_user):
        super().__init__(session, current_user)
    
    @event_publisher("my_event")
    def do_something(self):
        return {"data": "value"}
    
    @event_subscriber("other_event")
    def on_other_event(self, **kwargs):
        pass
```

자세한 내용은 `docs/event_manager_SUMMARY.md` 참고

## 📚 문서

- [Simple Event Bus 요약](../../docs/event_manager_SUMMARY.md)
- [마이그레이션 가이드](../../docs/event_manager_MIGRATION_GUIDE.md)
- [기본 예제](../../examples/event_manager_example.py)
- [실제 프로젝트 예제](../../examples/real_world_example_service.py)

