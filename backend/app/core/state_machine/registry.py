"""
상태 머신 레지스트리 - 등록된 상태 머신 관리
"""

from typing import Any, Dict, Type, Optional, TYPE_CHECKING, Union
from pydantic import BaseModel

if TYPE_CHECKING:
    from .base import StateMachine


class StateMachineRegistry:
    """상태 머신 레지스트리 - 모듈 레벨 싱글톤"""

    _machines: Dict[str, Dict[str, Any]] = {}  # name -> {class, allowed_transitions}
    _transition_models_cache: Dict[str, Type[BaseModel]] = (
        {}
    )  # 캐싱: machine_name -> BaseModel
    # _machine_info_cache: Dict[str, Type[BaseModel]] = (
    #     {}
    # ) # 캐싱: machine_name -> BaseModel
    @classmethod
    def register(
        cls,
        name: str,
        machine_class: Type["StateMachine"],
        allowed_transitions: Optional[Dict] = None,
    ):
        """상태 머신 등록"""
        cls._machines[name] = {
            "class": machine_class,
            "allowed_transitions": allowed_transitions or {},
        }

    @classmethod
    def get_machine(cls, name: str) -> Optional[Type["StateMachine"]]:
        """상태 머신 조회"""
        machine_info = cls._machines.get(name)
        return machine_info["class"] if machine_info else None

    @classmethod
    def get_allowed_transitions(cls, name: str) -> Optional[Dict]:
        """상태 머신의 allowed_transitions 조회"""
        machine_info = cls._machines.get(name)
        return machine_info["allowed_transitions"] if machine_info else None

    @classmethod
    def get_all_machines(cls) -> Dict[str, Type["StateMachine"]]:
        """모든 상태 머신 조회"""
        return {name: info["class"] for name, info in cls._machines.items()}

    @classmethod
    def get_machine_by_state(cls, state) -> Optional[Type["StateMachine"]]:
        """상태로 머신 조회"""
        for name, info in cls._machines.items():
            if state in info["allowed_transitions"]:
                return info["class"]
        return None

    @classmethod
    def get_transition_model(cls, machine_name: str) -> Type[BaseModel]:
        """
        등록된 상태머신의 transition BaseModel을 반환

        Args:
            machine_name: 상태머신 이름 (클래스 이름, 예: 'BuyStateMachine')

        Returns:
            Pydantic BaseModel 클래스

        Raises:
            ValueError: 머신이 등록되지 않았거나 모델 생성에 실패한 경우

        예시:
            response_model=StateMachineRegistry.get_transition_model('BuyStateMachine')
        """
        # 캐시에서 먼저 확인
        if machine_name in cls._transition_models_cache:
            return cls._transition_models_cache[machine_name]

        # 등록된 머신 조회
        machine_class = cls.get_machine(machine_name)
        if not machine_class:
            raise ValueError(f"StateMachine '{machine_name}'이 등록되지 않았습니다.")

        # 인스턴스 생성하여 BaseModel 생성
        try:
            instance: StateMachine = machine_class()
            model = instance.get_transition_model()
            # 캐시에 저장
            cls._transition_models_cache[machine_name] = model
            return model
        except Exception as e:
            raise ValueError(f"'{machine_name}'의 transition model 생성 실패: {e}")

    @classmethod
    def get_machine_info(cls,machine_name:Union[str, Type["StateMachine"]]) -> Type[BaseModel]:
        if isinstance(machine_name, type) :
            machine_name = machine_name.__name__
        """
        등록된 상태머신의 machine info BaseModel을 반환

        Args:
            machine_name: 상태머신 이름 (클래스 이름, 예: 'BuyStateMachine')

        Returns:
            Pydantic BaseModel 클래스

        Raises:
            ValueError: 머신이 등록되지 않았거나 모델 생성에 실패한 경우

        예시:
            response_model=StateMachineRegistry.get_transition_model('BuyStateMachine')
        """
        # if machine_name in cls._machine_info_cache:
        #     return cls._machine_info_cache[machine_name]
        machine_class = cls.get_machine(machine_name)
        if not machine_class:
            raise ValueError(f"StateMachine '{machine_name}'이 등록되지 않았습니다.")
        instance: StateMachine = machine_class()
        model = instance.get_machine_info()
        # cls._machine_info_cache[machine_name] = model
        return model
    @classmethod
    def print_transitions(cls, name: Optional[str] = None) -> str:
        """상태 머신의 전이 규칙을 한글로 번역해서 반환"""
        if name is None:
            return "\n".join(
                [cls.print_transitions(name) for name in cls._machines.keys()]
            )
        machine_info = cls._machines.get(name)
        if not machine_info:
            return f"상태 머신 '{name}'을 찾을 수 없습니다."

        allowed_transitions = machine_info["allowed_transitions"]
        if not allowed_transitions:
            return f"상태 머신 '{name}'에 전이 규칙이 없습니다."

        result = [f"상태 전이 규칙: {name}"]
        for from_state, to_states in allowed_transitions.items():
            if to_states:
                to_state_names = [s.value for s in to_states]
                result.append(f"  -{from_state.value} → {', '.join(to_state_names)}")
            else:
                result.append(f"  -{from_state.value} → 변경 불가 (최종 상태)")

        return "\n".join(result)

