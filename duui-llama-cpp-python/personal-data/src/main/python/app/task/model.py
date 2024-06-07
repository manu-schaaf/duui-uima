from typing import Literal

from app.model import BaseLlamaRequest
from app.task.query import AdvancedResponse, SimpleResponse
from pydantic import BaseModel


class LlamaRequest(BaseLlamaRequest):
    """The request model for the Llama DUUI component.
    Must be a subclass of BaseLlamaRequest.
    The type field acts as a switch for the different request types.
    The task specific logic is called if the type is 'task'.
    """

    text: str | None = None
    model: str | None = None
    language: Literal["en", "de"] = "de"
    variant: Literal["simple", "advanced"] = "advanced"

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "type": "task",
                    "text": (
                        "Here is some text containing personal information: "
                        "John Doe, 123 Main St, Springfield, IL 62701. "
                        "This is a test."
                    ),
                    "language": "en",
                    "variant": "advanced",
                },
            ]
        }
    }


class TaskSpecificResponse(BaseModel):
    """Task-specific response model"""

    response: SimpleResponse | AdvancedResponse
