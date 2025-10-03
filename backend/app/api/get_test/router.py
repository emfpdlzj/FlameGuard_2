from fastapi import APIRouter
from app.api.get_test.schema import GetTestSchema

router = APIRouter()


@router.get("/get_test", response_model=GetTestSchema)
def get_test():
    return {
        "message": "testget",
    }


@router.get("/get_test2", response_model=GetTestSchema)
def get_test2():
    return {
        "message": "testget",
    }
