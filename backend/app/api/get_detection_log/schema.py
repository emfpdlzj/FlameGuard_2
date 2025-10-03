from pydantic import BaseModel
from typing import List

from app.api.share_schema import DetectionLog


class GetDetectionLogResponse(BaseModel):
    items: List[DetectionLog]
    total_count: int

