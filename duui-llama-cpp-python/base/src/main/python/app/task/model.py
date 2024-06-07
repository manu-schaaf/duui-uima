from app.model import BaseLlamaRequest
from pydantic import BaseModel


class LlamaRequest(BaseLlamaRequest):
    """The request model for the Llama DUUI component.
    Must be a subclass of BaseLlamaRequest.
    The type field acts as a switch for the different request types.
    The task specific logic is called if the type is 'task'.
    """

    text: str | None = None
    model: str | None = None

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "task": "chat",
                    "body": {
                        "messages": [
                            {
                                "role": "system",
                                "content": "You are a helpful assistant.",
                            },
                            {
                                "role": "user",
                                "content": "What is the capital of France?",
                            },
                        ],
                    },
                },
                {
                    "task": "embedding",
                    "body": {
                        "input": "The food was delicious and the waiter...",
                    },
                },
                {
                    "task": "completion",
                    "body": {
                        "prompt": "\n\n### Instructions:\nWhat is the capital of France?\n\n### Response:\n",
                        "stop": ["\n", "###"],
                    },
                },
            ]
        }
    }


class TaskSpecificResponse(BaseModel):
    """Task-specific response model"""

    response: str


