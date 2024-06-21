ARG CUDA_VERSION="12.4.1"

FROM ghcr.io/mamba-org/micromamba:jammy-cuda-${CUDA_VERSION}

RUN micromamba install -y -n base -c conda-forge python=3.11 fastapi=0.110.3 uvicorn=0.30.1 gunicorn=22.0.0 && micromamba clean --all --yes

WORKDIR /duui

COPY ./lua/communication_layer.lua /duui/communication_layer.lua
COPY ./resources/dkpro-core-types.xml /duui/dkpro-core-types.xml
COPY ./python/wsgi.py /duui/wsgi.py
COPY ./python/app/*.py /duui/app/
COPY ./python/app/parser/*.py /duui/app/parser/

ENTRYPOINT ["/usr/local/bin/_entrypoint.sh"]