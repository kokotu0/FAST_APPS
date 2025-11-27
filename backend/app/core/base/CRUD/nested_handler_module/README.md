# Nested Handler Module

중첩된 관계(Nested Relationship) 처리를 위한 모듈화된 패키지입니다.

## 📁 구조

```
nested_handler_module/
├── __init__.py              # 패키지 초기화 및 exports
├── README.md               # 이 파일
├── types.py                # 타입 정의
├── utils.py                # 유틸리티 함수들
├── metadata_manager.py     # 메타데이터 관리
├── model_inspector.py      # 모델 검사 및 정보 추출
├── data_processor.py       # 중첩 데이터 처리
├── relationship_updater.py # 관계 업데이트 처리
└── handler.py              # 메인 핸들러 클래스
```

## 🎯 주요 특징

### 1. 모듈화된 설계
- **단일 책임 원칙**: 각 모듈이 하나의 명확한 책임을 가짐
- **느슨한 결합**: 모듈 간 의존성 최소화
- **높은 응집도**: 관련 기능들을 논리적으로 그룹화

### 2. 타입 안전성
- **강력한 타이핑**: TypeVar, Generic, Protocol 활용
- **런타임 검증**: 타입 가드 함수들로 안전성 확보
- **명확한 인터페이스**: 각 컴포넌트의 입출력 타입 명시

### 3. 설정 기반 동작
- **관계별 설정**: 각 관계마다 다른 처리 방식 적용 가능
- **중복 해결 전략**: 다양한 중복 키 처리 방식 지원
- **Soft Delete 지원**: 관계별로 soft delete 설정 가능

## 🚀 사용법

### 기본 사용법

```python
from core.base.CRUD.nested_handler_module import NestedRelationshipHandler, RelationshipConfig

# 핸들러 생성
handler = NestedRelationshipHandler(
    session=session,
    user=current_user,
)

# 중첩 생성
instance = handler.create_with_nested(MyModel, data)

# 중첩 업데이트
updated_instance = handler.update_with_nested(instance, new_data, MyRequestSchema)
```

### 고급 설정

```python
from core.base.CRUD.nested_handler_module import (
    NestedRelationshipHandler, 
    RelationshipConfig,
    DuplicateResolutionStrategy
)

# 관계별 설정
configs = {
    "details": RelationshipConfig(
        key_fields={"name", "code"},
        exclude_fields={"created_at", "updated_at"},
        soft_delete_column="deleted",
        duplicate_strategy=DuplicateResolutionStrategy.UPSERT,
    ),
    "attachments": RelationshipConfig(
        key_fields={"filename"},
        duplicate_strategy=DuplicateResolutionStrategy.RAISE_ERROR,
    )
}

handler = NestedRelationshipHandler(
    session=session,
    user=current_user,
    relationship_configs=configs,
)
```

## 🔧 컴포넌트 상세

### MetadataManager
- 생성/수정 시간, 생성자/수정자 자동 관리
- Soft delete 메타데이터 처리
- Base 클래스의 공통 필드 자동 설정

### DataProcessor
- 중첩된 데이터의 재귀적 처리
- 순환 참조 감지 및 방지
- 타입 안전한 데이터 변환

### RelationshipUpdater
- OneToMany, OneToOne 관계 업데이트
- ModelComparator 기반 변화 감지
- 중복 해결 전략 적용

### ModelInspector
- SQLModel의 관계, 컬럼 정보 추출
- Base 스키마 자동 추출
- 모델 메타데이터 분석

## 🎨 확장 가능성

### 새로운 중복 해결 전략 추가

```python
class CustomDuplicateStrategy(DuplicateResolutionStrategy):
    CUSTOM_STRATEGY = "custom_strategy"

# RelationshipUpdater에서 새 전략 처리 로직 추가
```

### 커스텀 메타데이터 필드

```python
class CustomMetadataManager(MetadataManager):
    def add_custom_metadata(self, data, custom_field):
        data[custom_field] = custom_value
```

## 🧪 테스트

각 컴포넌트는 독립적으로 테스트 가능:

```python
# 개별 컴포넌트 테스트
def test_metadata_manager():
    manager = MetadataManager(user)
    data = {}
    manager.add_creation_metadata(data)
    assert "created_by" in data

def test_data_processor():
    processor = NestedDataProcessor()
    result = processor.process_nested_data(data, Model)
    assert isinstance(result, dict)
```

## 🔄 마이그레이션

기존 `nested_handler.py`에서 마이그레이션:

```python
# 기존 방식
from core.base.CRUD.nested_handler import NestedRelationshipHandler as OldHandler

# 새로운 방식
from core.base.CRUD.nested_handler_module import NestedRelationshipHandler as NewHandler

# 동일한 인터페이스로 사용 가능
```

## 📈 성능 고려사항

- **지연 로딩**: 필요한 컴포넌트만 초기화
- **캐싱**: 모델 정보 캐싱으로 반복 검사 최소화
- **배치 처리**: 여러 관계를 한 번에 처리

## 🐛 디버깅

각 컴포넌트별로 독립적인 로깅:

```python
import logging

# 특정 컴포넌트만 디버그 모드
logging.getLogger('nested_handler_module.data_processor').setLevel(logging.DEBUG)
```

## 🔮 향후 계획

1. **비동기 지원**: async/await 패턴 지원
2. **캐싱 레이어**: Redis 등을 활용한 캐싱
3. **이벤트 시스템**: 관계 변경 시 이벤트 발생
4. **성능 모니터링**: 처리 시간 및 메모리 사용량 추적
























