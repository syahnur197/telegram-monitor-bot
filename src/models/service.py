from typing import Optional
from datetime import datetime
from sqlmodel import SQLModel, Field


class Service(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    url: str
    is_up: bool = True
    last_checked_at: Optional[datetime] = None
    first_down_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
