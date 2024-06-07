import traceback

from fastapi.testclient import TestClient
from llama_cpp.server.app import Settings, create_app

MODEL = "/app/test/ggml-vocab-llama.gguf"


def test_server():
    settings = Settings(
        model=MODEL,
        vocab_only=True,
    )
    app = create_app(settings)
    client = TestClient(app)
    response = client.get("/v1/models")
    expected = {
        "object": "list",
        "data": [
            {
                "id": MODEL,
                "object": "model",
                "owned_by": "me",
                "permissions": [],
            }
        ],
    }
    if response.json() != expected:
        print("Did not get expected response")
        print("Expected:")
        print(expected)
        print("Got:")
        print(response.json())

        exit(-2)


if __name__ == "__main__":
    try:
        test_server()
    except Exception:
        traceback.print_exc()
        exit(-1)

    exit(0)




