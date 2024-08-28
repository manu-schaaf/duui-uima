ARG BASE_VERSION="0.5.1"
ARG VERSION="0.0.1"
ARG CUDA_NAME="cu124"
ARG CUDA_VERSION="12.4.1"

FROM docker.texttechnologylab.org/duui-slc-base/${CUDA_NAME}:${BASE_VERSION} as base

FROM ghcr.io/mamba-org/micromamba:jammy-cuda-${CUDA_VERSION} as mamba

RUN micromamba install -y -n base -c conda-forge python=3.11 fastapi=0.110.3 uvicorn=0.30.1 gunicorn=22.0.0 && micromamba clean --all --yes

FROM mamba as biaffine

USER root

ARG MAMBA_DOCKERFILE_ACTIVATE=1
ENV PATH=/opt/conda/bin/:$PATH

RUN micromamba install -y -n base -c conda-forge pip stanza=1.8.2 && micromamba clean --all --yes
RUN apt-get update && apt-get install -y git

RUN pip install transformers==4.30.0
RUN pip install -U git+https://github.com/yzhangcs/parser

ENV ANNOTATOR_NAME="duui-slc-biaffine"
ENV VERSION="${VERSION}"

FROM biaffine as app

WORKDIR /duui

COPY --from=base /duui /duui
COPY ./python/app/parser/*.py /duui/app/parser/
COPY ./python/app/parser/models /duui/app/parser/models

ENTRYPOINT [ "gunicorn", "wsgi:app", "-b", "0.0.0.0:9714", "-k", "uvicorn.workers.UvicornWorker", "--timeout", "3600" ]
CMD [ "-w", "1" ]
