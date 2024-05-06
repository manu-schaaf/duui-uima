FROM docker.texttechnologylab.org/llm/hf:latest as fetch

RUN huggingface-cli download TheBloke/Mixtral-8x7B-Instruct-v0.1-GGUF mixtral-8x7b-instruct-v0.1.Q5_K_M.gguf

FROM docker.texttechnologylab.org/llm/llama-cpp-python:latest as component

WORKDIR /app/
COPY ./config.json /app/
COPY --from=fetch /root/.cache/huggingface/hub /root/.cache/huggingface/hub

CMD gunicorn wsgi:app -b ${HOST}:${PORT} -k uvicorn.workers.UvicornWorker
