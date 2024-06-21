import logging
import os
import time
import traceback
from pathlib import Path
from threading import Lock
from typing import Generator

from app.abc import ModelProxyABC
from app.model import (
    DuuiCapability,
    DuuiDocumentation,
    DuuiRequest,
    DuuiResponse,
    ErrorMessage,
)
from app.parser import ParserProxy, DependencyParser
from app.parser import __meta__ as parser_meta
from fastapi import Depends, FastAPI, Request, Response
from fastapi.responses import JSONResponse, PlainTextResponse

logger = logging.getLogger(__name__)

v1_api = FastAPI()


@v1_api.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    logger.info(f"{request.url.path}: {process_time*1000:0.0f}ms")
    return response


lua_path = Path(os.environ.get("COMMUNICATION_LAYER_PATH", "communication_layer.lua"))

if lua_path.exists():
    logger.debug("Loading Lua communication layer from file")
    with lua_path.open("r", encoding="utf-8") as f:
        lua_communication_layer = f.read()
else:
    raise FileNotFoundError(f"Lua communication layer not found: {lua_path}")


@v1_api.get("/v1/communication_layer", response_class=PlainTextResponse, tags=["DUUI"])
def get_communication_layer() -> str:
    """Get the LUA communication script"""
    return lua_communication_layer


type_system_path = Path(os.environ.get("TYPE_SYSTEM_PATH", "dkpro-core-types.xml"))
if (type_system_path).exists():
    logger.debug("Loading type system from file")
    with type_system_path.open("r", encoding="utf-8") as f:
        type_system = f.read()
else:
    raise FileNotFoundError(f"Type system not found: {type_system_path}")


@v1_api.get("/v1/typesystem", tags=["DUUI"])
def get_typesystem() -> Response:
    """Get typesystem of this annotator"""
    return Response(content=type_system, media_type="application/xml")


@v1_api.get("/v1/documentation", tags=["DUUI"])
def get_documentation() -> DuuiDocumentation:
    """Get documentation info"""
    capabilities = DuuiCapability(
        supported_languages=["en", "de"],
        reproducible=True,
    )

    annotator_name = os.environ.get("ANNOTATOR_NAME")
    version = os.environ.get("VERSION", "0.0.1")
    documentation = DuuiDocumentation(
        annotator_name=annotator_name,
        version=version,
        implementation_lang="Python",
        meta=parser_meta,
        docker_container_id=os.environ.get(
            "DOCKER_CONTAINER_ID",
            f"docker.texttechnologylab.org/{annotator_name}:{version}",
        ),
        parameters={},
        capability=capabilities,
        implementation_specific=None,
    )

    return documentation


lock = Lock()

_model_proxy: ModelProxyABC = ParserProxy()


def get_proxy() -> Generator[ModelProxyABC, None, None]:
    lock.acquire()
    try:
        yield _model_proxy
    finally:
        lock.release()


@v1_api.post(
    "/v1/process",
    response_model=DuuiResponse,
    responses={
        400: {
            "model": ErrorMessage,
            "description": "An error occurred while processing the request.",
        },
    },
    tags=["DUUI"],
)
async def v1_process(
    request: DuuiRequest,
    proxy=Depends(get_proxy),  # noqa: B008
):
    try:
        return DependencyParser.with_proxy(proxy).process(request)
    except Exception as e:
        logger.error(f"Error in v1_process: {e}\n{traceback.format_exc()}")
        return JSONResponse(
            status_code=400,
            content={
                "message": f"Error in v1_process: {e}",
                "traceback": traceback.format_exc().splitlines(),
            },
        )
