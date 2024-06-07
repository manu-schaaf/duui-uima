from app.task.model import LlamaRequest, TaskSpecificResponse
from fastapi import Depends
from llama_cpp.server.app import get_llama_proxy


async def task_specific_process(
    body: LlamaRequest,
    llama_proxy=Depends(get_llama_proxy),
) -> TaskSpecificResponse:
    llama = llama_proxy(body.model)
    raise NotImplementedError(
        "Task-specific logic not implemented for pure llama-cpp-python DUUI component!"
    )


