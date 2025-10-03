from typing import Optional
from fastapi import APIRouter, Depends

from sqlalchemy.orm import Session

# api의 요청 응답 구조를 정의
from app.api.get_detection_log.schema import GetDetectionLogResponse

# 데이터베이스 연결 함수
from app.db.database import get_db

# crud 함수
from app.api.get_detection_log.crud import (
    get_detection_logs,
    get_total_detection_logs_count,
)

router = APIRouter()


@router.get("/get_detection_log", response_model=GetDetectionLogResponse)
def get_detection_log(
    page: Optional[int] = 0,
    page_size: Optional[int] = 15,
    filter: Optional[str] = None,
    db: Session = Depends(get_db),
):
    items = get_detection_logs(
        db, skip=(page - 1) * page_size, limit=page_size, filter=filter
    )

    total_count = get_total_detection_logs_count(db)

    return {"items": items, "total_count": total_count}
