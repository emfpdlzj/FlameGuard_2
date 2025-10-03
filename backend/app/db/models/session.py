from sqlalchemy import Column, Integer, DateTime, JSON, String
from sqlalchemy.sql import func
import pytz
from datetime import datetime
from app.db.database import Base

# session models/: 데이터베이스 모델을 정의합니다.


class Session(Base):
    __tablename__ = "sessions"

    id = Column(String, primary_key=True, index=True)
    user_id = Column(Integer, unique=True, index=True)
    data = Column(JSON)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(pytz.timezone("Asia/Seoul")),
    )
    last_accessed_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(pytz.timezone("Asia/Seoul")),
        onupdate=lambda: datetime.now(pytz.timezone("Asia/Seoul")),
    )
    expires_at = Column(DateTime(timezone=True))
