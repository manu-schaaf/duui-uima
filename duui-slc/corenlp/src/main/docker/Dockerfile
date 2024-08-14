ARG BASE_VERSION="0.5.1"
ARG VERSION="0.0.1"
ARG CUDA_NAME="cu124"
ARG CUDA_VERSION="12.4.1"

FROM docker.texttechnologylab.org/duui-slc-base/${CUDA_NAME}:${BASE_VERSION} as base

FROM ghcr.io/mamba-org/micromamba:jammy-cuda-${CUDA_VERSION} as mamba

RUN micromamba install -y -n base -c conda-forge python=3.11 fastapi=0.110.3 uvicorn=0.30.1 gunicorn=22.0.0 && micromamba clean --all --yes

FROM mamba as corenlp

USER root
RUN apt-get update && apt-get install -y openjdk-17-jdk && apt-get clean

RUN micromamba install -y -n base -c conda-forge stanza=1.8.2 && micromamba clean --all --yes

ARG MAMBA_DOCKERFILE_ACTIVATE=1
ENV PATH=/opt/conda/bin/:$PATH

RUN python -c "import stanza; stanza.install_corenlp(); stanza.download_corenlp_models(model='german', version='4.5.7');"

ENV ANNOTATOR_NAME="duui-slc-corenlp"
ENV VERSION="${VERSION}"

FROM corenlp as app

WORKDIR /duui

COPY --from=base /duui /duui
COPY ./python/app/parser/*.py /duui/app/parser/

ENTRYPOINT [ "gunicorn", "wsgi:app", "-b", "0.0.0.0:9714", "-k", "uvicorn.workers.UvicornWorker", "--timeout", "3600" ]
CMD [ "-w", "1" ]
