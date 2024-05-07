import logging
import os
import sys
import traceback
from pathlib import Path

import llama_cpp
from app.model import DUUICapability, DUUIDocumentation, ErrorMessage
from app.task.model import LlamaRequest, TaskSpecificResponse
from app.task.process import task_specific_process
from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import JSONResponse, PlainTextResponse
from llama_cpp.server.app import (
    create_chat_completion,
    create_completion,
    create_embedding,
    get_llama_proxy,
)
from llama_cpp.server.model import LlamaProxy
from llama_cpp.server.types import (
    CreateChatCompletionRequest,
    CreateCompletionRequest,
    CreateEmbeddingRequest,
)

# Import all from task, enables developers to override base classes
try:
    from app.task import *
except ImportError:
    pass

v1_api = APIRouter()

logger = logging.getLogger("fastapi")


lua_communication_layer = ""
if (path := Path("lua_communication_layer.lua")).exists():
    logger.debug("Loading Lua communication layer from file")
    with path.open("r", encoding="utf-8") as f:
        lua_communication_layer = f.read()
else:
    logger.warning("Lua communication layer not found")


@v1_api.get("/v1/communication_layer", response_class=PlainTextResponse, tags=["DUUI"])
def get_communication_layer() -> str:
    """Get the LUA communication script"""
    return lua_communication_layer


type_system = ""
if (path := Path("typesystem.xml")).exists():
    logger.debug("Loading type system from file")
    with path.open("r", encoding="utf-8") as f:
        type_system = f.read()


@v1_api.get("/v1/typesystem", tags=["DUUI"])
def get_typesystem() -> Response:
    """Get typesystem of this annotator"""
    return Response(content=type_system, media_type="application/xml")


@v1_api.get("/v1/documentation", tags=["DUUI"])
def get_documentation() -> DUUIDocumentation:
    """Get documentation info"""
    capabilities = DUUICapability(
        supported_languages=["en"],
        reproducible=True,
    )

    documentation = DUUIDocumentation(
        annotator_name="llama-cpp-python",
        version="0.0.1",
        implementation_lang="Python",
        meta={
            "sys.version": sys.version,
            "llama_cpp.__version__": llama_cpp.__version__,
        },
        docker_container_id=f"docker.texttechnologylab.org/llm/llama-cpp-python:{os.environ.get('VERSION', 'latest')}",
        parameters={},
        capability=capabilities,
        implementation_specific=None,
    )

    return documentation


@v1_api.post(
    "/v1/process",
    response_model=(
        TaskSpecificResponse
        | llama_cpp.CreateChatCompletionResponse
        | llama_cpp.CreateCompletionResponse
        | llama_cpp.CreateEmbeddingResponse
    ),
    responses={
        400: {
            "model": ErrorMessage,
            "description": "An error occurred while processing the request.",
        },
    },
    tags=["DUUI"],
)
async def v1_process(
    request: Request,
    llama_request: LlamaRequest,
    llama_proxy: LlamaProxy = Depends(get_llama_proxy),
):
    try:
        match llama_request.type:
            case "chat":
                return await create_chat_completion(
                    request=request,
                    body=CreateChatCompletionRequest(**llama_request.body),
                    llama_proxy=llama_proxy,
                )
            case "completion" | "completions":
                return await create_completion(
                    request=request,
                    body=CreateCompletionRequest(**llama_request.body),
                    llama_proxy=llama_proxy,
                )
            case "embedding":
                return await create_embedding(
                    request=CreateEmbeddingRequest(**llama_request.body),
                    llama_proxy=llama_proxy,
                )
            case _:
                return await task_specific_process(
                    body=llama_request,
                    llama_proxy=llama_proxy,
                )
    except Exception as e:
        logger.error(f"Error in v1_process: {e}\n{traceback.format_exc()}")
        return JSONResponse(
            status_code=400,
            content={
                "message": f"Error in v1_process: {e}",
                "traceback": traceback.format_exc().splitlines(),
            },
        )
