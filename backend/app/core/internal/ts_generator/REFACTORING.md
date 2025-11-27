# TypeScript Generator - 리팩토링 가이드

## 개요

`TsGenerater.py`의 990줄 단일 파일을 **관심사 분리(Separation of Concerns)** 원칙에 따라 7개의 모듈로 리팩토링했습니다.

## 폴더 구조

```
core/internal/ts_generator/
├── __init__.py              # 공개 API 제공
├── base_types.py            # 기본 타입 정의 및 상수
├── type_converter.py        # Python → TypeScript 타입 변환
├── router_extractor.py      # 라우터에서 스키마/라우트 추출
├── code_generator.py        # TypeScript 코드 생성
├── file_manager.py          # 파일 생성 및 관리
├── utils.py                 # 유틸리티 함수
└── REFACTORING.md           # 이 문서
```

## 각 모듈의 책임

### 1. **base_types.py** - 기본 타입 정의
**책임**: TypeScript 기본 타입 상수와 설정 관리

```python
# 제공하는 것:
- BASE_TYPES: 기본 타입 집합
- BASE_TYPES_STRING: TypeScript 기본 타입 정의 문자열
- BASE_URL: API 베이스 URL
- Authorization: API 요청 헤더
- format_types_to_export(): import 문 생성
```

**변경 영향**: BASE_URL이나 기본 타입이 변경되면 이 파일만 수정

---

### 2. **utils.py** - 유틸리티 함수
**책임**: 공통적으로 사용되는 헬퍼 함수들

```python
# 제공하는 것:
- normalize_content_for_hash(): 파일 내용 정규화
- extract_valid_params(): 라우터 파라미터 추출
- extract_basemodel_types(): BaseModel 타입 재귀 추출
```

**변경 영향**: 정규화 로직이나 타입 추출 로직이 변경되면 이 파일만 수정

---

### 3. **type_converter.py** - 타입 변환 로직
**책임**: Python 타입 ↔ TypeScript 타입 변환

```python
# 핵심 함수:
- get_type_name(field_type) → (ts_type_str, is_nullable)
  * int → "number"
  * str → "string"
  * List[Enum] → "(EnumValue1 | EnumValue2)[]"
  * Dict[str, int] → "Record<string, number>"

- generate_typescript_types(model) → TypeScript interface
  * Pydantic 모델을 TypeScript 인터페이스로 변환
  * Enum 필드 특별 처리

- generate_enum_arrays(model) → TypeScript enum 배열
  * 모델의 Enum 필드를 TypeScript 상수로 변환
```

**변경 영향**: 
- 새로운 Python 타입 지원 추가: `get_type_name()` 확장
- Enum 처리 방식 변경: `extract_enum_from_union()` 수정
- 타입 매핑 규칙 변경: `TYPE_MAPPING` 수정

---

### 4. **router_extractor.py** - 라우터 추출
**책임**: FastAPI 라우터에서 스키마와 라우트 정의 추출

```python
# 핵심 함수:
- extract_all_routers(file_path) → Dict[name, APIRouter]
  * Python 파일 동적 로드
  * 모든 APIRouter 인스턴스 추출

- extract_schemas_from_router(router) → Set[BaseModel]
  * 라우터에서 사용되는 모든 스키마 수집
  * 중첩 스키마도 재귀적으로 추출

- extract_routes_from_router(router) → Dict[route_name, route_def]
  * 라우터의 모든 라우트 정의 추출
  * 메서드, 경로, 파라미터, 응답 모델 정보 포함
```

**변경 영향**:
- 라우터 구조 변경: `extract_all_routers()` 수정
- 새로운 라우트 메타데이터 지원: `RouteDefinition` 확장

---

### 5. **code_generator.py** - 코드 생성
**책임**: TypeScript 코드 생성 로직

```python
# 핵심 함수:
- generate_router_content(routers, name, base_url) → TypeScript class
  * 라우트 정의를 TypeScript 클래스로 변환
  * 각 라우트별 static async 메서드 생성
  * HTTP 메서드에 따른 fetch 호출 코드 생성
  * JSDoc 주석 자동 생성

내부 함수들:
- format_request_type(): 파라미터 타입 포맷
- format_response_type(): 응답 타입 포맷
- generate_method_body(): HTTP 메서드 구현 코드
- format_jsdoc(): Python docstring → JSDoc
```

**변경 영향**:
- 생성된 메서드 서명 변경: `format_request_type()` 수정
- 요청/응답 처리 방식 변경: `generate_method_body()` 수정
- 문서화 형식 변경: `format_jsdoc()` 수정

---

### 6. **file_manager.py** - 파일 I/O 및 관리
**책임**: TypeScript 파일 생성, 관리, 변경 감지

```python
# 핵심 함수:
- analyze_routers_file(py_path, ts_path, ts_path) → TypeScript content
  * 모든 라우터 분석 및 TypeScript 코드 생성
  * 스키마, 라우트, Enum 배열 모두 포함

- find_route_files(base_dir, ts_base_dir) → List[Tuple]
  * api/ 디렉토리에서 routes.py 파일들 검색
  * Python 경로 ↔ TypeScript 경로 매핑

- Generate_TsFile(ts_base_dir)
  * 모든 라우터 파일을 TypeScript로 변환
  * 해시 기반 변경 감지 (성능 최적화)
  * 더 이상 필요 없는 파일 자동 삭제

- Generate_specific_TsFile(ts_path)
  * base_types.ts 파일 생성
  * 기본 타입 정의 업데이트
```

**변경 영향**:
- 파일 생성 규칙 변경: `analyze_routers_file()` 수정
- 파일 탐색 로직 변경: `find_route_files()` 수정
- 변경 감지 방식 변경: `Generate_TsFile()` 수정

---

## 사용 예제

### 기본 사용

```python
from core.internal.ts_generator import Generate_TsFile, Generate_specific_TsFile

# 모든 라우터 파일을 TypeScript로 변환
Generate_TsFile(ts_base_dir="../frontend/src/routers")

# base_types.ts 파일 생성
Generate_specific_TsFile(ts_path="../frontend/src/")
```

### 개별 함수 사용

```python
from core.internal.ts_generator import (
    extract_all_routers,
    extract_schemas_from_router,
    generate_typescript_types,
)

# 라우터 추출
routers = extract_all_routers("api/product/routes.py")

# 스키마 추출
for name, router in routers.items():
    schemas = extract_schemas_from_router(router)
    
    # TypeScript 타입 생성
    for schema in schemas:
        ts_code = generate_typescript_types(schema)
        print(ts_code)
```

---

## 리팩토링 이점

### 1. **단일 책임 원칙 (Single Responsibility Principle)**
- 각 모듈은 하나의 명확한 책임을 가짐
- 변경 영향 범위 최소화
- 테스트 용이성 증대

### 2. **코드 재사용성**
- 각 모듈을 독립적으로 임포트 가능
- 필요한 기능만 선택적으로 사용 가능
- 다른 프로젝트에서도 재사용 가능

### 3. **유지보수성**
- 990줄 → 각 파일 100~300줄로 축소
- 함수의 목적이 명확함
- 버그 추적과 수정 용이

### 4. **확장성**
- 새로운 타입 지원 추가: `type_converter.py`만 수정
- 새로운 코드 생성 방식: `code_generator.py`만 수정
- 새로운 파일 관리 방식: `file_manager.py`만 수정

### 5. **테스트 용이**
```python
# 각 모듈을 독립적으로 테스트 가능
def test_type_converter():
    assert get_type_name(int) == ("number", False)
    assert get_type_name(List[str]) == ("string[]", False)

def test_router_extractor():
    routers = extract_all_routers("api/test/routes.py")
    assert len(routers) > 0

def test_code_generator():
    content = generate_router_content({}, "Test")
    assert "export class Test" in content
```

---

## 마이그레이션 가이드

### 기존 코드

```python
from core.internal.TsGenerater import Generate_TsFile

Generate_TsFile(ts_base_dir="../frontend/src/routers")
```

### 리팩토링된 코드

```python
from core.internal.ts_generator import Generate_TsFile

Generate_TsFile(ts_base_dir="../frontend/src/routers")
```

**변경사항**: `TsGenerater` → `ts_generator` (소문자로 변경)

---

## 향후 개선 계획

1. **캐싱 최적화**: 반복되는 타입 변환 결과 캐시
2. **플러그인 시스템**: 사용자 정의 타입 변환기 지원
3. **설정 파일**: YAML/JSON 기반 TypeScript 생성 설정
4. **증분 빌드**: 변경된 파일만 다시 생성
5. **테스트 생성**: TypeScript 테스트 코드 자동 생성

---

## 참고

- **공식 문서**: [TypeScript Generator](/docs/ts_generator.md)
- **원본 파일**: `core/internal/TsGenerater.py` (리팩토링 전)

