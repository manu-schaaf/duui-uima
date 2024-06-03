import logging
import os
import sys
import traceback
from threading import Lock
from pathlib import Path

from pydantic import BaseModel
import spacy
from app.model import (
    DUUICapability,
    DUUIDocumentation,
    DUUIRequest,
    ErrorMessage,
    Offset,
    SpaCyAnnotations,
)
from app.process import post_process
from fastapi import APIRouter, Depends, Response
from fastapi.responses import JSONResponse, PlainTextResponse

v1_api = APIRouter()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


lua_communication_layer = ""
if (
    path := Path(
        os.environ.get("COMMUNICATION_LAYER_PATH", "lua_communication_layer.lua")
    )
).exists():
    logger.debug("Loading Lua communication layer from file")
    with path.open("r", encoding="utf-8") as f:
        lua_communication_layer = f.read()
else:
    raise FileNotFoundError("Lua communication layer not found")


@v1_api.get("/v1/communication_layer", response_class=PlainTextResponse, tags=["DUUI"])
def get_communication_layer() -> str:
    """Get the LUA communication script"""
    return lua_communication_layer


type_system = ""
if (path := Path(os.environ.get("TYPE_SYSTEM_PATH", "dkpro-core-types.xml"))).exists():
    logger.debug("Loading type system from file")
    with path.open("r", encoding="utf-8") as f:
        type_system = f.read()
else:
    raise FileNotFoundError("Type system not found")


@v1_api.get("/v1/typesystem", tags=["DUUI"])
def get_typesystem() -> Response:
    """Get typesystem of this annotator"""
    return Response(content=type_system, media_type="application/xml")


@v1_api.get("/v1/documentation", tags=["DUUI"])
def get_documentation() -> DUUIDocumentation:
    """Get documentation info"""
    capabilities = DUUICapability(
        supported_languages=["en", "de"],
        reproducible=True,
    )

    documentation = DUUIDocumentation(
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

# model_en = "en_core_web_trf"
model_en = "en_core_web_sm"
# model_de = "de_dep_news_trf"
model_de = "de_core_news_sm"
model_map = {
    "en": model_en,
    "en_US": model_en,
    "en_GB": model_en,
    "en_AU": model_en,
    "en_CA": model_en,
    "de": model_de,
    "de_DE": model_de,
    "de_AT": model_de,
    "de_CH": model_de,
}


class SpaCyModelProxy:
    def __init__(self):
        self.models = {}

    def __getitem__(self, lang: str):
        lang = model_map.get(lang.replace("-", "_"), lang)
        if self.models.get(lang) is None:
            logger.info(f"load({lang})")
            nlp = spacy.load(
                lang,
                disable=[
                    "parser",
                    "ner",
                ],
            )
            nlp.add_pipe("sentencizer")
            self.models[lang] = nlp
            logger.info(f"load({lang}): done")
        return self.models[lang]


_spacy_model_proxy = SpaCyModelProxy()


def get_pipeline():
    lock.acquire()
    try:
        yield _spacy_model_proxy
    finally:
        lock.release()


@v1_api.post(
    "/v1/process",
    response_model=SpaCyAnnotations,
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

        results = post_process(
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
