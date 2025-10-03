from sqlalchemy.orm import Session
from app.api.create_user.schema import create_user_schema
from app.db.models.user import User as user_model
from datetime import datetime, timedelta, timezone
from app.utils.password import hash_password, verify_password


def create_user(db: Session, user: create_user_schema):
    expiration_date = datetime.now(timezone.utc) + timedelta(days=7)
    hashed_password = hash_password(user.password)
    # verifiedTest = verify_password(hashed_password, user.password)
    db_user = user_model(
        email=user.email,
        password=hashed_password,  # hashed password
        verified=False,
        role="user",
        plan="free",
        expired_at=expiration_date,
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user
