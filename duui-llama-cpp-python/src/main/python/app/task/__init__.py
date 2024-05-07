import llama_cpp
from fastapi import Depends
from llama_cpp.server.app import get_llama_proxy
from pydantic import BaseModel


class TaskSpecificRequestBody(BaseModel):
    text: str
    model: str | None = None


class TaskSpecificResponse(BaseModel):
    """Task-specific response model"""

    response: str


async def task_specific_logic(
    body: TaskSpecificRequestBody,
    llama_proxy=Depends(get_llama_proxy),
) -> TaskSpecificResponse:
    llama = llama_proxy(body.model)
    raise NotImplementedError(
        "Task-specific logic not implemented for pure llama-cpp-python DUUI component!"
    )
