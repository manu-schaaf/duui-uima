ARG VERSION="latest"
FROM docker.texttechnologylab.org/llm/llama-cpp-python/base:${VERSION}

ENV HOST 0.0.0.0
ENV PORT 9714
ENV SSL_KEYFILE=
ENV SSL_CERTFILE=
ENV CONFIG_FILE /app/config.json

WORKDIR /app/
COPY ./config.json /app/

CMD gunicorn wsgi:app -b ${HOST}:${PORT} -k uvicorn.workers.UvicornWorker
