"""
공통 상태 전이 머신 베이스 클래스

모든 도메인의 상태 전이 규칙을 위한 공통 인터페이스 제공
"""

from types import NoneType
from typing import Optional, Set, TypeVar, Generic, List, Type, Any, Dict
from enum import Enum
from fastapi import HTTPException

from pydantic import BaseModel, create_model, Field
from pydantic_core import core_schema

from .metaclass import StateMachineMeta
from .registry import StateMachineRegistry
import logging
logger = logging.getLogger(__name__)
StateType = TypeVar("StateType", bound=Enum)


class Never:
    """전이 불가능한 상태를 나타내는 마커 타입"""

    def __repr__(self) -> str:
        return "Never"

    @classmethod
    def __get_pydantic_core_schema__(
        cls, source_type: Any, handler
    ) -> core_schema.CoreSchema:
        """Pydantic v2 호환성을 위한 schema 정의"""
        return core_schema.with_info_plain_validator_function(
            lambda v, _: v,
            serialization=core_schema.plain_serializer_function_ser_schema(
                lambda instance: None,
                return_schema=core_schema.none_schema(),
            ),
        )


class StateMachine(Generic[StateType], metaclass=StateMachineMeta):
    """
    상태 전이 머신 베이스 클래스

    각 도메인별 상태 전이 규칙을 정의할 때 상속받아 사용
    allowed_transitions: 상태 전이 규칙
    entry_points: 진입 가능점

    """

    def __init__(
        self,
        allowed_transitions: Dict[StateType, Set[StateType]] = {},
        entry_points: Set[StateType] = set(),
        order: Dict[StateType, int] = {},
        
    ):
        self.ALLOWED_TRANSITIONS: Dict[StateType, Set[StateType]] = allowed_transitions
        self.ENTRY_POINTS: Set[StateType] = (
            entry_points if entry_points else set(self.ALLOWED_TRANSITIONS.keys())
        )
        self.ORDER: Dict[StateType, int] = (
            order
            if order
            else {
                state: index
                for index, state in enumerate(self.ALLOWED_TRANSITIONS.keys())
            }
        )
        self.states = list[StateType](self.ALLOWED_TRANSITIONS.keys())

    def can_initialize(self, status: StateType) -> bool:
        """
        상태 초기화 가능 여부 검증

        Args:
            status: 초기화하려는 상태
        """
        return status in self.ENTRY_POINTS

    def can_transition(self, from_status: StateType, to_status: StateType) -> bool:
        """
        상태 전이 가능 여부 검증

        Args:
            from_status: 현재 상태
            to_status: 변경하려는 상태

        Returns:
            전이 가능 여부
        """
        # 동일 상태로의 전이는 허용 (멱등성)
        if from_status == to_status:
            return True

        # 기본 전이 규칙 체크
        allowed_states = self.ALLOWED_TRANSITIONS.get(from_status, set())
        return to_status in allowed_states

    def validate_transition(self, from_status: StateType, to_status: StateType) -> None:
        """
        상태 전이 유효성 검증 (예외 발생)

        Args:
            from_status: 현재 상태
            to_status: 변경하려는 상태

        Raises:
            HTTPException: 잘못된 상태 전이인 경우
        """
        if not self.can_transition(from_status, to_status):
            allowed_states = self.ALLOWED_TRANSITIONS.get(from_status, set())
            allowed_names = [s.value for s in allowed_states]
            raise HTTPException(
                status_code=400,
                detail=f"잘못된 상태 전이: {from_status.value} → {to_status.value}. "
                f"허용되는 상태: {', '.join(allowed_names) if allowed_names else '없음'}",
            )

    def get_next_allowed_states(self, current_status: Optional[StateType] = None) -> List[StateType]:
        """
        현재 상태에서 전이 가능한 상태 목록 반환

        Args:
            current_status: 현재 상태

        Returns:
            전이 가능한 상태 목록
        """
        if not current_status:
            return list(self.ENTRY_POINTS)
        allowed_states = self.ALLOWED_TRANSITIONS.get(current_status, set()) 
        allowed_states = list(allowed_states) +  [current_status]
        return allowed_states

    def get_transition_reason(
        self, from_status: StateType, to_status: StateType
    ) -> str:
        """
        상태 전이에 대한 설명 반환

        하위 클래스에서 오버라이드하여 구체적인 설명 제공
        """
        return f"{from_status.value} → {to_status.value}"

    def get_transition_model(self) -> Type[BaseModel]:
        """
        동적으로 전이 규칙 BaseModel 생성
        각 상태별 다음 가능한 상태들을 List[Enum]로 표현

        예시:
        - 대기중: [Enum('처리중'), Enum('취소됨')]
        - 처리중: [Enum('입고중'), Enum('보류'), Enum('취소됨')]
        - 입고중: [] (전이 불가능)
        - 취소됨: [] (전이 불가능)
        """
        fields = {}

        for status, allowed in self.ALLOWED_TRANSITIONS.items():
            field_name = status.value

            # allowed 상태들의 value만 추출
            allowed_values = [s.value for s in allowed]

            if allowed_values:
                # 동적 Enum 생성: 각 상태별로 다른 Enum 클래스 생성 (set → list로 변환하여 순서 고정)
                sorted_allowed_values = list(sorted(set(allowed_values)))
                DynamicEnum = Enum(
                    f"TransitionEnum_{field_name}",
                    {val: val for val in sorted_allowed_values},
                    type=str,
                )
                # default는 DynamicEnum의 모든 값들
                fields[field_name] = (
                    List[DynamicEnum],
                    Field(
                        default=[getattr(DynamicEnum, val) for val in allowed_values]
                    ),
                )
            else:
                # 전이 불가능한 상태 (빈 리스트)
                fields[field_name] = (Never, Field(default=Never))

        # 동적으로 모델 생성
        TransitionModel = create_model(
            f"{self.__class__.__name__}TransitionModel", **fields
        )
        return TransitionModel

    def get_order_model(self) -> Type[BaseModel]:
        """
        상태별 순서를 Pydantic 모델로 반환

        Returns:
            {
                "대기중": 0,
                "처리중": 1,
                ...
            }
        """
        fields = {
            state.value: (int, Field(default=self.ORDER.get(state, index)))
            for index, state in enumerate(self.ORDER.keys())
        }
        OrderModel = create_model(
            f"{self.__class__.__name__}OrderModel", **fields  # type:ignore
        )  # pyright: ignore[reportCallIssue, reportArgumentType]
        return OrderModel

    def get_machine_info(self) -> Type[BaseModel]:
        """
        머신 정보를 Pydantic 모델로 반환

        Returns:
            {
                "allowed_transitions": {
                    "대기중": ["처리중", "취소됨"],
                    "처리중": ["입고중", "보류", "취소됨"],
                    "입고중": ["정상완료", "취소됨"],
                    "정상완료": null,
                    "취소됨": null
                },
                "entry_points": []
            }
        """

        def get_allowed_transitions_dict() -> Dict[str, Any]:
            """상태별 전이 가능한 상태들을 딕셔너리로 변환"""
            result = {}
            for from_state, to_states in self.ALLOWED_TRANSITIONS.items():
                if to_states:
                    # 전이 가능한 상태들의 value 리스트
                    result[from_state.value] = [s.value for s in to_states]
                else:
                    # 전이 불가능 (최종 상태) - 빈 리스트로 반환
                    result[from_state.value] = []
            return result

        def get_order_dict() -> Dict[str, Any]:
            """상태별 순서를 딕셔너리로 변환"""
            return {
                state.value: self.ORDER.get(state, index)
                for index, state in enumerate(self.ORDER.keys())
            }

        transition_model = self.get_transition_model()
        order_model = self.get_order_model()
        StateMachineInfo = create_model(
            f"{self.__class__.__name__}StateMachineInfo",
            name=(
                str,
                Field(default=self.__class__.__name__),
            ),
            order=(order_model, Field(default_factory=get_order_dict)),
            allowed_transitions=(
                transition_model,
                Field(default_factory=get_allowed_transitions_dict),
            ),
            entry_points=(
                List[StateType],
                Field(default=list[StateType](self.ENTRY_POINTS)),
            ),
        )
        return StateMachineInfo

    @property
    def transition_model(self) -> Type[BaseModel]:
        return self.get_transition_model()

    @property
    def entry_points(self) -> Set[StateType]:
        return self.ENTRY_POINTS

    @property
    def name(self) -> str:
        return self.__class__.__name__

    def to_transition_map(self) -> Dict[str, Any]:
        """
        상태 전이 정보를 딕셔너리로 변환

        Returns:
            {
                'transitions': [
                    {
                        'from_status': '대기중',
                        'from_status_code': 'PENDING',
                        'to_statuses': ['처리중', '취소됨'],
                        'to_status_codes': ['PROCESSING', 'CANCELLED']
                    },
                    ...
                ],
                'enum_map': {
                    'PENDING': '대기중',
                    'PROCESSING': '처리중',
                    ...
                }
            }
        """
        transitions = []
        enum_map = {}

        for from_status, to_statuses in self.ALLOWED_TRANSITIONS.items():
            # Enum name과 value 추출
            from_status_code = from_status.name
            from_status_value = from_status.value

            # enum_map에 등록
            enum_map[from_status_code] = from_status_value

            # 다음 상태들 추출
            to_statuses_values = [s.value for s in to_statuses]
            to_status_codes = [s.name for s in to_statuses]

            # enum_map에 다음 상태들도 등록
            for status in to_statuses:
                if status.name not in enum_map:
                    enum_map[status.name] = status.value

            transitions.append(
                {
                    "from_status": from_status_value,
                    "from_status_code": from_status_code,
                    "to_statuses": to_statuses_values,
                    "to_status_codes": to_status_codes,
                }
            )

        return {"transitions": transitions, "enum_map": enum_map}


def get_changable_state(state_type: StateType) -> List[StateType]:
    """
    특정 상태에서 변경 가능한 상태 목록 조회

    Args:
        state_type: 현재 상태

    Returns:
        변경 가능한 상태 목록
    """
    # 상태로 머신 직접 조회 (더 효율적)
    machine_class = StateMachineRegistry.get_machine_by_state(state_type)

    if not machine_class:
        # 백업: 모든 머신에서 찾기
        for name, info in StateMachineRegistry._machines.items():
            if state_type in info["allowed_transitions"]:
                machine_class = info["class"]
                break

    if not machine_class:
        raise ValueError(
            f"상태 '{state_type.value}'를 처리하는 상태 머신을 찾을 수 없습니다."
        )

    # 상태 머신 인스턴스 생성
    machine = machine_class()
    return machine.get_next_allowed_states(state_type)
