import logging
import os
import sys
import traceback
from pathlib import Path
from typing import Literal, Optional

import llama_cpp
from app.task import TaskSpecificRequestBody, TaskSpecificResponse, task_specific_logic
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
from pydantic import BaseModel

v1_api = APIRouter()

logger = logging.getLogger("fastapi")


if (path := Path("lua_communication_layer.lua")).exists():
    logger.debug("Loading Lua communication layer from file")
    with path.open("r", encoding="utf-8") as f:
        lua_communication_script = f.read()
else:
    pass
    # raise RuntimeError("Lua communication layer not found!")


@v1_api.get("/v1/communication_layer", response_class=PlainTextResponse)
def get_communication_layer() -> str:
    """Get the LUA communication script"""
    return lua_communication_script


type_system = ""
if (path := Path("dkpro-core-types.xml")).exists():
    logger.debug("Loading type system from file")
    with path.open("r", encoding="utf-8") as f:
        type_system = f.read()


@v1_api.get("/v1/typesystem")
def get_typesystem() -> Response:
    """Get typesystem of this annotator"""
    return Response(content=type_system, media_type="application/xml")


class DUUICapability(BaseModel):
    """Capability response model"""

    # List of supported languages by the annotator
    # TODO how to handle language?
    # - ISO 639-1 (two letter codes) as default in meta data
    # - ISO 639-3 (three letters) optionally in extra meta to allow a finer mapping
    supported_languages: list[str]
    # Are results on same inputs reproducible without side effects?
    reproducible: bool


class DUUIDocumentation(BaseModel):
    """Documentation response model"""

    # Name of this annotator
    annotator_name: str
    # Version of this annotator
    version: str
    # Annotator implementation language (Python, Java, ...)
    implementation_lang: Optional[str]
    # Optional map of additional meta data
    meta: Optional[dict]
    # Docker container id, if any
    docker_container_id: Optional[str]
    # Optional map of supported parameters
    parameters: Optional[dict]
    # Capabilities of this annotator
    capability: DUUICapability
    # Analysis engine XML, if available
    implementation_specific: Optional[str]


@v1_api.get("/v1/documentation")
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


class LlamaRequestBody(BaseModel):
    """Request model"""

    type: Literal["chat", "completion", "embedding", "task"] = "chat"
    body: dict


class ErrorMessage(BaseModel):
    message: str
    traceback: Optional[list[str]]


class DUUIResponse(BaseModel):
    llama_response: (
        TaskSpecificResponse
        | llama_cpp.CreateChatCompletionResponse
        | llama_cpp.CreateCompletionResponse
        | llama_cpp.CreateEmbeddingResponse
    )


@v1_api.post(
    "/v1/process",
    response_model=DUUIResponse,
    responses={
        400: {
            "model": ErrorMessage,
            "description": "There was an error with the request",
        },
    },
)
async def v1_process(
    request: Request,
    llama_request: LlamaRequestBody,
    llama_proxy: LlamaProxy = Depends(get_llama_proxy),
):
    try:
        match llama_request.type:
            case "chat":
                response = await create_chat_completion(
                    request=request,
                    body=CreateChatCompletionRequest(**llama_request.body),
                    llama_proxy=llama_proxy,
                )
            case "completion":
                response = await create_completion(
                    request=request,
                    body=CreateCompletionRequest(**llama_request.body),
                    llama_proxy=llama_proxy,
                )
            case "embedding":
                response = await create_embedding(
                    request=CreateEmbeddingRequest(**llama_request.body),
                    llama_proxy=llama_proxy,
                )
            case "task":
                response = await task_specific_logic(
                    body=TaskSpecificRequestBody(**llama_request.body),
                    llama_proxy=llama_proxy,
                )
            case _:
                return JSONResponse(
                    status_code=400,
                    content={
                        "message": f"Invalid request type: '{llama_request.type}'"
                    },
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
    return DUUIResponse(
        llama_response=response,
    )
