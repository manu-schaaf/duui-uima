ARG CUDA_VERSION="12.4.1"

FROM ghcr.io/mamba-org/micromamba:jammy-cuda-${CUDA_VERSION}

RUN micromamba install -y -n base -c conda-forge python=3.11 fastapi=0.110.3 uvicorn=0.30.1 gunicorn=22.0.0 && micromamba clean --all --yes

ARG MAMBA_DOCKERFILE_ACTIVATE=1
ENV PATH=/opt/conda/bin/:$PATH

WORKDIR /duui

COPY ./lua/communication_layer.lua ./communication_layer.lua
COPY ./resources/dkpro-core-types.xml ./dkpro-core-types.xml
COPY ./python/app/*.py ./app/
COPY ./python/wsgi.py ./wsgi.py

ENTRYPOINT ["/usr/local/bin/_entrypoint.sh"]