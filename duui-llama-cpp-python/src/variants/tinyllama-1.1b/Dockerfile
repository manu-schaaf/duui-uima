# build layer for fetching the model that may be reused
FROM docker.texttechnologylab.org/llm/hf:latest as fetch

RUN huggingface-cli download TheBloke/TinyLlama-1.1B-Chat-v1.0-GGUF tinyllama-1.1b-chat-v1.0.Q2_K.gguf

# build layer for the actual component
FROM docker.texttechnologylab.org/llm/llama-cpp-python:latest as component
COPY --from=fetch /root/.cache/huggingface/hub /root/.cache/huggingface/hub

WORKDIR /app/
COPY ./config.json /app/

CMD gunicorn wsgi:app -b ${HOST}:${PORT} -k uvicorn.workers.UvicornWorker
