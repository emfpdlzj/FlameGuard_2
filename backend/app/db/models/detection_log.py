from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Integer,
    String,
    JSON,
    ForeignKey,
)
from sqlalchemy.orm import relationship
from app.db.database import Base
import pytz
from datetime import datetime


# logs models/: 데이터베이스 모델을 정의합니다.
class DetectionLog(Base):
    __tablename__ = "detection_logs"

    id = Column(Integer, primary_key=True, index=True)
    # user_id = Column(
    #     Integer, ForeignKey("users.id"), nullable=False
    # )  # User 모델과의 관계 설정
    file_name = Column(String)  # 원본 이미지 파일명
    result_image = Column(String)  # 처리된 결과 이미지 경로
    detections = Column(JSON)  # 감지된 객체들의 정보 (class_name, confidence, bbox 등)
    message = Column(String)  # 처리 결과 메시지
    has_fire = Column(Boolean, default=False)  # 화재 감지 여부
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(pytz.timezone("Asia/Seoul")),
    )

    # User 모델과의 관계 설정
    # user = relationship("User", back_populates="detection_logs")
