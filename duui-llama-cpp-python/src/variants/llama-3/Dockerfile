ARG CUDA_VERSION="cu124"
ARG BASE_VERSION="latest"
# base layer for the component
FROM docker.texttechnologylab.org/llm/llama-cpp-python/${CUDA_VERSION}/base:${BASE_VERSION} as base

FROM docker.texttechnologylab.org/llm/hf:latest as fetch
RUN huggingface-cli download NousResearch/Meta-Llama-3-8B-Instruct-GGUF Meta-Llama-3-8B-Instruct-Q5_K_M.gguf

FROM docker.texttechnologylab.org/llm/llama-cpp-python/${CUDA_VERSION}/deps:${BASE_VERSION} as component
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
