import datetime
from uuid import UUID, uuid4
from sqlmodel import JSON, Column, Field, SQLModel
from typing import Any, Dict, List, Optional

from app.core.model import Base


class FormBase(SQLModel):
    uuid: str = Field(max_length=36, unique=True, index=True)
    category: str = Field(min_length=1, max_length=255)
    title: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=255)
    JSONSchema: Dict[str, Any] = Field(default={}, sa_column=Column(JSON))
    UISchema: Dict[str, Any] = Field(default={}, sa_column=Column(JSON))
    Theme: str = Field(default="mui")
    useYN: bool = Field(default=True)

class FormTemplate(FormBase, Base):
    pass


class FormTable(FormTemplate,table=True):
    pass

class FormPublishBase(SQLModel):
    form_idx: int = Field(foreign_key="formtable.idx")
    receiver :str
    token:str
    expired_at: datetime.datetime = Field(default_factory=lambda: datetime.datetime.now() + datetime.timedelta(days=30))
    responseSchema: Dict[str, Any] = Field(default={}, sa_column=Column(JSON))
class FormPublishTemplate(FormPublishBase, Base): 
    pass
    
class FormPublishTable(FormPublishTemplate, table=True):
    pass
