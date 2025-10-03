from pydantic import BaseModel


class GetTestSchema(BaseModel):
    message: str
