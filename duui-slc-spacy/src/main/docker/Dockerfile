ARG CUDA_VERSION="cu124"
ARG BASE_VERSION="0.0.1"
FROM docker.texttechnologylab.org/duui-slc-spacy/${CUDA_VERSION}/base:${BASE_VERSION}

WORKDIR /duui

COPY ./lua/communication_layer.lua ./communication_layer.lua
COPY ./resources/dkpro-core-types.xml ./dkpro-core-types.xml
COPY ./python/wsgi.py ./wsgi.py
COPY ./python/app/ ./app/

ENTRYPOINT [ "gunicorn", "wsgi:app", "-b", "0.0.0.0:9714", "-k", "uvicorn.workers.UvicornWorker" ]
CMD [ "-w", "1" ]