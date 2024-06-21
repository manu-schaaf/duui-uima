"""
Taken from: https://github.com/abetlen/llama-cpp-python/blob/main/llama_cpp/server/__main__.py
"""

from __future__ import annotations

import os

import uvicorn
from app.duui import v1_api as app

__all__ = ["app"]

if __name__ == "__main__":
    uvicorn.run(
        "wsgi:app",
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", 9714)),
        log_level="info",
    )
