from pydantic import BaseModel, HttpUrl
from datetime import datetime
from typing import Optional

class Item(BaseModel):
    url: HttpUrl
    status: str
    videoTitle: str
    time_created: datetime = datetime.utcnow()
    time_updated: Optional[datetime] = None

class UpdateItem(BaseModel):
    url: Optional[str] = None
    status: Optional[str] = None
    videoTitle: Optional[str] = None
    time_updated: datetime = datetime.utcnow()