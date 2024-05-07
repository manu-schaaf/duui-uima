"""
Taken from: https://github.com/abetlen/llama-cpp-python/blob/main/llama_cpp/server/__main__.py
"""

from __future__ import annotations

import os

import uvicorn
from app.duui import v1_api as duui_v1_api
from app.llama import llama_cpp_app


def app():
    app = llama_cpp_app()

    # DUUI v1 interface
    app.include_router(duui_v1_api)

    return app


if __name__ == "__main__":
    uvicorn.run(
        app(),
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", 9714)),
        ssl_keyfile=os.getenv("SSL_KEYFILE", None),
        ssl_certfile=os.getenv("SSL_CERTFILE", None),
        log_level="info",
    )
