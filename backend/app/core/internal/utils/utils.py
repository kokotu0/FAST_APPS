import difflib
import functools
import copy
import importlib.util
import inspect
import os
import re
import sys
import logging
import hashlib
from typing import Any, Dict, List
from typing_extensions import deprecated
from fastapi import APIRouter
import sqlalchemy
from sqlmodel import SQLModel, Sequence, Session

import logging
logger = logging.getLogger(__name__)


def get_file_hash(content: str) -> str:
    """
    파일 내용의 해시를 생성하되, 일관성을 위해 정규화 수행
    - 줄바꿈 문자 통일 (\r\n, \r -> \n)
    - 끝에 있는 공백 제거
    - 파일 끝 줄바꿈 통일
    - import 문의 타입 순서 정렬
    """
    import re

    # 줄바꿈 문자 통일
    normalized_content = content.replace("\r\n", "\n").replace("\r", "\n")

    # import 문의 타입 순서 정렬
    lines = normalized_content.split("\n")
    normalized_lines = []

    for line in lines:
        # import type { ... } 형태의 줄 찾기
        import_match = re.match(r"(\s*)import type \{ ([^}]+) \} from '([^']+)'", line)
        if import_match:
            indent, types_str, from_path = import_match.groups()
            # 타입들을 분리하고 정렬
            types = [t.strip() for t in types_str.split(",")]
            sorted_types = sorted(types)
            # 정렬된 타입들로 다시 조합
            sorted_types_str = ", ".join(sorted_types)
            normalized_line = (
                f"{indent}import type {{ {sorted_types_str} }} from '{from_path}'"
            )
            normalized_lines.append(normalized_line)
        else:
            normalized_lines.append(line)

    # 각 줄의 끝 공백 제거
    normalized_lines = [line.rstrip() for line in normalized_lines]

    # 빈 줄들을 파일 끝에서 제거 (하지만 중간 빈 줄은 유지)
    while normalized_lines and not normalized_lines[-1]:
        normalized_lines.pop()

    # 하나의 줄바꿈으로 끝나도록 통일
    normalized_content = "\n".join(normalized_lines)
    if normalized_content and not normalized_content.endswith("\n"):
        normalized_content += "\n"

    return hashlib.md5(normalized_content.encode("utf-8")).hexdigest()


# utils.py 전용 로거 생성 (비활성화)
UTILS_LOGGER = logging.getLogger(__name__)
UTILS_LOGGER.disabled = True

# 다른 모듈에서 사용할 수 있도록 기존 LOGGER는 그대로 유지
# logger = logger  # 이미 import되어 있음


def validate_item_category_path(code, expected_prefix: str):
    if not code.path.startswith(expected_prefix):
        raise ValueError(f"{expected_prefix} 경로에 속한 코드만 사용할 수 있습니다.")


def convert_mappings_to_model(mapping_results, model_class):
    return [model_class(**item) for item in mapping_results]


def find_files(base_dir: str = "api", pattern=r"routes\.py$") -> List[str]:
    route_files = []
    pattern = re.compile(pattern)

    if not os.path.exists(base_dir):
        raise FileNotFoundError(f"Directory '{base_dir}' does not exist")

    for root, _, files in os.walk(base_dir):
        for file in files:
            if pattern.search(file):
                # routes.py 파일 경로
                py_path = os.path.join(root, file).replace("\\", "/")

                route_files.append(py_path)

    return sorted(route_files)


from typing import Type, Union, Callable, Any


def load_module_members(
    file_path: str,
    type_filter: Union[Type, tuple[Type, ...], None] = None,
    predicate: Callable[[Any], bool] | None = None,
):
    """
    Python 파일을 동적으로 로드하고 조건에 맞는 멤버들을 추출

    Args:
        file_path: 로드할 파일 경로
        type_filter: 필터링할 타입 또는 타입들의 튜플
        predicate: 커스텀 필터링 함수
    """
    module_name = f"dynamic_module_{file_path.replace('/', '_')}"
    if module_name in sys.modules:
        del sys.modules[module_name]

    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)  # type: ignore
    spec.loader.exec_module(module)  # type: ignore

    result = {}

    def default_predicate(obj):
        if predicate is not None:
            return predicate(obj)
        if type_filter is not None:
            return isinstance(obj, type_filter)
        return True  # type_filter와 predicate가 모두 None이면 모든 객체 반환

    for name, obj in inspect.getmembers(module, default_predicate):
        result[name] = obj

    return result


from fastapi import FastAPI


def regist_all_routers(app: FastAPI,base_dir:str = "api",pattern:str = r"routes\.py$"):
    files = find_files(base_dir=base_dir,pattern=pattern)
    # 커스텀 조건으로 검색
    for file in files:
        routers = load_module_members(
            file,
            predicate=lambda obj: hasattr(obj, "router")
            and isinstance(obj.router, APIRouter),
        )
        routers.update(
            load_module_members(
                file,
                predicate=lambda obj: isinstance(obj, APIRouter),
            )
        )

        for router in routers.values():
            if hasattr(router, "router"):
                app.include_router(router.router)
            else:
                app.include_router(router)


from typing import Any, Dict, List, Set, Tuple, Union, Optional
from datetime import datetime, date
from enum import Enum
from sqlmodel import SQLModel
from sqlalchemy.engine.row import Row
import inspect


@deprecated("deprecated")
def orm_to_query(query, print=True):
    from sqlalchemy.dialects import postgresql

    sql_query = query.compile(
        dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True}
    )
    from pprint import pprint

    if print:
        pprint(sql_query)
    else:
        return sql_query


@deprecated("deprecated")
def sqlmodel_to_json(
    obj: Any, exclude_fields: Set[str] | None = None, max_depth: int = 5
) -> Any:
    """
    SQLModel/SQLAlchemy 객체를 JSON 직렬화 가능한 형태로 변환

    Args:
        obj: 변환할 객체
        exclude_fields: 제외할 필드 이름 집합
        max_depth: 재귀 깊이 제한

    Returns:
        JSON 직렬화 가능한 객체
    """
    if exclude_fields is None:
        exclude_fields = {"hashed_password", "password"}

    if max_depth <= 0:
        return None

    # 기본 타입 처리
    if obj is None or isinstance(obj, (str, int, float, bool)):
        return obj

    # 열거형 처리
    if isinstance(obj, Enum):
        return obj

    # 날짜/시간 처리
    if isinstance(obj, (datetime, date)):
        return obj

    # 리스트 처리
    if isinstance(obj, list):
        return [sqlmodel_to_json(item, exclude_fields, max_depth - 1) for item in obj]

    # 딕셔너리 처리
    if isinstance(obj, dict):
        return {
            k: sqlmodel_to_json(v, exclude_fields, max_depth - 1)
            for k, v in obj.items()
            if k not in exclude_fields
        }

    # SQLModel 객체 처리
    if isinstance(obj, SQLModel):
        return {
            k: sqlmodel_to_json(v, exclude_fields, max_depth - 1)
            for k, v in obj.dict().items()
            if k not in exclude_fields
        }

    # SQLAlchemy 모델 객체 처리
    if hasattr(obj, "__table__"):
        result = {}
        for key, value in inspect.getmembers(obj):
            if key.startswith("_") or callable(value) or key in exclude_fields:
                continue
            result[key] = sqlmodel_to_json(value, exclude_fields, max_depth - 1)
        return result

    # Row/RowMapping 처리
    if hasattr(obj, "_mapping"):
        return sqlmodel_to_json(dict(obj._mapping), exclude_fields, max_depth - 1)

    # 일반 객체는 문자열로 변환
    try:
        return str(obj)
    except Exception:
        return None


@deprecated("deprecated")
def Row_to_object(result):
    if isinstance(result, (List)):
        return list(map(Row_to_object, result))

    import sqlalchemy

    if not isinstance(result, sqlalchemy.engine.row.Row):
        raise ValueError("잘못된 변수 삽입 -sqlalchemy.engine.row.Row가 아님.")

    structured_result = {}
    # row._mapping을 통해 별칭 정보에 접근
    mapping = result._mapping

    for key, value in mapping.items():
        # 키 이름으로 별칭 사용
        if isinstance(key, str):
            structured_result[key] = value
        else:
            # 클래스 이름 사용 (기존 방식)
            type_name = type(value).__name__
            if type_name not in structured_result:
                structured_result[type_name] = value
            else:
                structured_result[f"{type_name}_{list(mapping.keys()).index(key)}"] = (
                    value
                )

    return structured_result


from typing import TypeVar, Callable, ParamSpec

T = TypeVar("T")
P = ParamSpec("P")


def session_wrapper(exit_with_commit: bool = True):
    """
    SQLModel 세션을 자동으로 주입하는 데코레이터입니다.

    세션 관리를 자동화하여 트랜잭션 처리를 간편하게 해주는 데코레이터입니다.
    데코레이터가 적용된 함수의 첫 번째 인자로 세션이 자동 주입됩니다.

    Args:
        exit_with_commit (bool): 세션 종료 시 커밋 여부를 결정하는 플래그
            - True: 정상 종료 시 자동으로 커밋 수행 (기본값)
            - False: 커밋을 수행하지 않고 세션만 종료

    예시:
        >>> @session_wrapper()
        >>> def get_sales_order(session: Session, order_id: int):
        >>>     return session.get(SalesOrder, order_id)

        >>> @session_wrapper(exit_with_commit=False)
        >>> def read_only_function(session: Session):
        >>>     return session.query(User).all()

    Raises:
        Exception: 세션 처리 중 오류 발생 시 자동으로 롤백 수행
    """
    from core.database import get_session
    import functools

    class exitCommitSession(Session):
        def __init__(self, session=None, *args, **kwargs):
            if not session:
                raise ValueError("session is required")
            self.session = session
            # session을 engine에 바인딩
            if hasattr(session, "bind") and session.bind:
                super().__init__(bind=session.bind, *args, **kwargs)
            else:
                super().__init__(*args, **kwargs)

        def __enter__(self):
            try:
                return self
            except Exception as e:
                self.rollback()
                raise e

        def __exit__(self, exc_type, exc_value, traceback):
            try:
                if exc_type is not None:
                    # 예외가 발생하면 롤백
                    self.rollback()
                else:
                    if exit_with_commit:
                        # 정상 종료면 커밋
                        self.commit()
            except Exception as e:
                self.rollback()
                raise e
            finally:
                self.close()

    def fn_wrapper(func: Callable[P, T]) -> Callable[P, T]:
        @functools.wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            session = get_session()
            try:
                if exit_with_commit:
                    with exitCommitSession(session) as managed_session:
                        # session을 첫 번째 위치 인자로 전달
                        UTILS_LOGGER.debug("session_wrapper - exit_with_commit")
                        return func(managed_session, *args, **kwargs)
                else:
                    with session as managed_session:
                        UTILS_LOGGER.debug("session_wrapper - not exit_with_commit")
                        return func(managed_session, *args, **kwargs)
            finally:
                UTILS_LOGGER.warning("session close")
                # session 정리
                session.close()

        return wrapper

    return fn_wrapper
