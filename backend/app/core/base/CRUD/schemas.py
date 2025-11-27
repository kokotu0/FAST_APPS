from pydantic import BaseModel
from typing import Dict, List, Optional, Generic, TypeVar
from core.state_machine.schema import StateMachineSchema

T = TypeVar("T")


class StandardResponseMeta(BaseModel):
    total_count: Optional[int] = 0
    failed_count: Optional[int] = 0
    success_count: Optional[int] = 0



class StandardResponse(BaseModel, Generic[T]):
    success: bool
    message: str
    data: T
    meta: Optional[StandardResponseMeta] = None

class StateMachineResponse(BaseModel):
    column_name: str
    states: List[str]
    transitable_states: List[str]
    order: Dict[str, int]
    