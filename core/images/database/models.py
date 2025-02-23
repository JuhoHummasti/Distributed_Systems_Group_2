from pydantic import BaseModel, HttpUrl
from datetime import datetime
from typing import Optional

class Item(BaseModel):
    video_id: str
    status: str
    title: str
    time_created: datetime = datetime.utcnow()
    time_updated: Optional[datetime] = None

class UpdateItem(BaseModel):
    video_id: Optional[str] = None
    status: Optional[str] = None
    title: Optional[str] = None
    time_updated: Optional[datetime] = None