ARG VERSION="latest"
# base layer for the component
FROM docker.texttechnologylab.org/llm/llama-cpp-python/base:${VERSION} as base

# layer(s) for fetching the model that may be reused
FROM docker.texttechnologylab.org/llm/hf:latest as fetch-q2k
RUN huggingface-cli download TheBloke/TinyLlama-1.1B-Chat-v1.0-GGUF tinyllama-1.1b-chat-v1.0.Q2_K.gguf

FROM docker.texttechnologylab.org/llm/hf:latest as fetch-q3ks
RUN huggingface-cli download TheBloke/TinyLlama-1.1B-Chat-v1.0-GGUF tinyllama-1.1b-chat-v1.0.Q3_K_S.gguf

# final layer for the actual component
FROM docker.texttechnologylab.org/llm/llama-cpp-python/deps:${VERSION} as component

# copy fetched model(s)
COPY --from=fetch-q2k /root/.cache/huggingface/hub /root/.cache/huggingface/hub
COPY --from=fetch-q3ks /root/.cache/huggingface/hub /root/.cache/huggingface/hub

# copy app code from base layer
COPY --from=base /app/ /app/

# set env vars
ENV HOST 0.0.0.0
ENV PORT 9714
ENV SSL_KEYFILE=
ENV SSL_CERTFILE=
ENV CONFIG_FILE /app/config.json

# set workdir and copy config
WORKDIR /app/
COPY ./config.json /app/

CMD gunicorn wsgi:app -b ${HOST}:${PORT} -k uvicorn.workers.UvicornWorker
