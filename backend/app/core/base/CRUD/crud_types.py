from typing import TypeVar, Union
from sqlmodel import SQLModel

from core.base.model import Base

ModelType = TypeVar("ModelType", bound=Base | SQLModel)
RequestModel = TypeVar("RequestModel", bound=SQLModel)  
ResponseModel = TypeVar("ResponseModel", bound=Base | SQLModel)
