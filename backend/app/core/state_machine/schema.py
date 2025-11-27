from pydantic import BaseModel
from typing import Dict, List, Any, Optional



class StateMachineSchema(BaseModel):
    name: str
    allowed_transitions: Dict[str, Optional[List[Any]]]
    entry_points: List[Any]
    order: Dict[str, int]

