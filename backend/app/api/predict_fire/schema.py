from pydantic import BaseModel
from typing import List, Dict, Any, Union


# 이미지 처리 결과의 단일 탐지 정보 모델
class Detection(BaseModel):
    class_name: str
    confidence: float
    bbox: List[float]


class PredictFireSchema(BaseModel):
    message: str
    file_name: Union[str, None]
    detections: List[Detection]
    result_image: Union[str, None]
    date: str
