from typing import Literal

from pydantic import BaseModel


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
    implementation_lang: str | None
    # Optional map of additional meta data
    meta: dict | None
    # Docker container id, if any
    docker_container_id: str | None
    # Optional map of supported parameters
    parameters: dict | None
    # Capabilities of this annotator
    capability: DUUICapability
    # Analysis engine XML, if available
    implementation_specific: str | None


class BaseLlamaRequest(BaseModel):
    """Request model"""

    # TODO: change to "completions"
    type: Literal["chat", "completion", "embedding", "task"] = "task"
    body: dict | None = None


class ErrorMessage(BaseModel):
    message: str
    traceback: list[str] | None
