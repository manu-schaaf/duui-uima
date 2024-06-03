import logging
import os
import sys
import traceback
from pathlib import Path
from threading import Lock

import spacy
from app.model import (
    DuuiCapability,
    DuuiDocumentation,
    DUUIRequest,
    DuuiResponse,
    ErrorMessage,
    Offset,
)
from app.specific import SpecificModelProxy, SpecificPostProcessor
from fastapi import APIRouter, Depends, Response
from fastapi.responses import JSONResponse, PlainTextResponse

v1_api = APIRouter()

logger = logging.getLogger(__name__)


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

    documentation = DuuiDocumentation(
        annotator_name="duui-slc-spacy",
        version="0.0.1",
        implementation_lang="Python",
        meta={
            "sys.version": sys.version,
            "spacy.__version__": spacy.__version__,
        },
        docker_container_id=f"docker.texttechnologylab.org/duui-slc-spacy:{os.environ.get('VERSION', 'latest')}",
        parameters={},
        capability=capabilities,
        implementation_specific=None,
    )

    return documentation


lock = Lock()

_model_proxy = SpecificModelProxy()


def get_pipeline():
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
    request: DUUIRequest,
    models=Depends(get_pipeline),  # noqa: B008
):
    logger.info(request)
    nlp = models[request.language]
    try:
        offsets = request.sentences or request.paragraphs
        if offsets:
            logger.info(f"Processing {len(offsets)} spans")
            annotations = []
            for offset in offsets:
                logger.info(f"Processing span {offset.begin} - {offset.end}")
                annotations.append(nlp(request.text[offset.begin : offset.end]))
        else:
            annotations = [nlp(request.text)]
            offsets = [Offset(begin=0, end=0)]

        results = SpecificPostProcessor.process(
            annotations,
            offsets,
        )

        return results
    except Exception as e:
        logger.error(f"Error in v1_process: {e}\n{traceback.format_exc()}")
        return JSONResponse(
            status_code=400,
            content={
                "message": f"Error in v1_process: {e}",
                "traceback": traceback.format_exc().splitlines(),
            },
        )