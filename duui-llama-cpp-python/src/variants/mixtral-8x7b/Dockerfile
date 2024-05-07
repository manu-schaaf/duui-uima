ARG VERSION="latest"
FROM docker.texttechnologylab.org/llm/llama-cpp-python/base:${VERSION} as base

FROM docker.texttechnologylab.org/llm/hf:latest as fetch
RUN huggingface-cli download TheBloke/Mixtral-8x7B-Instruct-v0.1-GGUF mixtral-8x7b-instruct-v0.1.Q5_K_M.gguf

FROM docker.texttechnologylab.org/llm/llama-cpp-python/deps:${VERSION} as component
COPY --from=fetch /root/.cache/huggingface/hub /root/.cache/huggingface/hub
COPY --from=base /app/ /app/

ENV HOST 0.0.0.0
ENV PORT 9714
ENV SSL_KEYFILE=
ENV SSL_CERTFILE=
ENV CONFIG_FILE /app/config.json

WORKDIR /app/
COPY ./config.json /app/

CMD gunicorn wsgi:app -b ${HOST}:${PORT} -k uvicorn.workers.UvicornWorker
