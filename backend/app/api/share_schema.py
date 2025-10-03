from pydantic import BaseModel
from datetime import datetime
from typing import List, Dict, Any, Optional

# common schema
class User(BaseModel):
    id: int
    email: str
    password: str
    count_login: int
    verified: bool
    role: str
    plan: str
    created_at: datetime
    expired_at: datetime

    class Config:
        from_attributes = True



class DetectionLog(BaseModel):
    id: int
    file_name: Optional[str] = None
    result_image: Optional[str] = None
    detections: List[Dict[str, Any]]
    message: str

    has_fire: bool
    created_at: datetime

    class Config:
        orm_mode = True
