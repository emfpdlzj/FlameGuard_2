from sqlalchemy.orm import Session, load_only
from app.db.models.user import User as user_model


# common crud
def get_user_by_email(db: Session, email: str):
    return (
        db.query(user_model)
        .options(
            load_only(
                user_model.email,
            )
        )
        .filter(user_model.email == email)
        .first()
    )
