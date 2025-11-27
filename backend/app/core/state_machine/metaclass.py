"""
상태 머신 메타클래스 - 자동 등록
"""

import logging
from typing import Type, cast, TYPE_CHECKING

from .registry import StateMachineRegistry

if TYPE_CHECKING:
    from .base import StateMachine


class StateMachineMeta(type):
    """상태 머신 메타클래스 - 자동 등록"""

    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)

    def __new__(mcs, name, bases, namespace):
        cls = super().__new__(mcs, name, bases, namespace)
        mcs.logger.debug(f"StateMachineMeta __new__: {name} {bases}")

        # StateMachine을 상속받는 클래스만 등록 (클래스 이름으로 확인)
        if bases and any(base.__name__ == "StateMachine" for base in bases):
            # 등록 전에 인스턴스 생성해서 allowed_transitions 추출
            allowed_transitions = {}
            try:
                temp_instance: StateMachine = cls()
                if hasattr(temp_instance, "ALLOWED_TRANSITIONS"):
                    allowed_transitions = temp_instance.ALLOWED_TRANSITIONS
                else:
                    mcs.logger.warning(f"{name} has no ALLOWED_TRANSITIONS attribute")
            except Exception as e:
                mcs.logger.error(f"Failed to initialize {name}: {e}")

            # name, cls, allowed_transitions 함께 등록
            StateMachineRegistry.register(
                name, cast(Type["StateMachine"], cls), allowed_transitions
            )

            # 등록 후 한글로 번역된 전이 규칙 로깅
            transition_log = StateMachineRegistry.print_transitions(name)
            mcs.logger.debug(transition_log)

        return cls

