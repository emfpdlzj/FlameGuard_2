from pydantic import BaseModel


class create_user_schema(BaseModel):
    email: str
    password: str
