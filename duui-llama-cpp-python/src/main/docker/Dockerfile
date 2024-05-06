ARG VERSION="0.1.0"
FROM docker.texttechnologylab.org/llm/llama-cpp-python/base:${VERSION}

ENV HOST="0.0.0.0"
ENV PORT="9714"
ENV SSL_KEYFILE=
ENV SSL_CERTFILE=
ENV CONFIG_FILE="/app/config.json"

WORKDIR /app/
COPY ./src/main/python/ /app/

CMD gunicorn wsgi:app -b ${HOST}:${PORT} -k uvicorn.workers.UvicornWorker
# ENTRYPOINT --keyfile ${SSL_KEYFILE} --certfile ${SSL_CERTFILE}