FROM docker.texttechnologylab.org/llm/hf:latest as fetch

RUN huggingface-cli download NousResearch/Meta-Llama-3-8B-Instruct-GGUF Meta-Llama-3-8B-Instruct-Q5_K_M.gguf

FROM docker.texttechnologylab.org/llm/llama-cpp-python/base:latest as component
COPY --from=fetch /root/.cache/huggingface/hub /root/.cache/huggingface/hub
COPY --from=docker.texttechnologylab.org/llm/llama-cpp-python:latest /app/ /app/

WORKDIR /app/
COPY ./config.json /app/

CMD gunicorn wsgi:app -b ${HOST}:${PORT} -k uvicorn.workers.UvicornWorker
