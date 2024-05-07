FROM docker.texttechnologylab.org/llm/llama-cpp-python:latest as component

WORKDIR /app/
COPY ./config.json /app/

CMD gunicorn wsgi:app -b ${HOST}:${PORT} -k uvicorn.workers.UvicornWorker
