ARG VERSION
ARG CUDA_NAME="cu124"
ARG CUDA_VERSION="12.4.1"

FROM docker.texttechnologylab.org/duui-slc-base/${CUDA_NAME}:${VERSION} as base

FROM ghcr.io/mamba-org/micromamba:jammy-cuda-${CUDA_VERSION} as mamba

RUN micromamba install -y -n base -c conda-forge python=3.11 fastapi=0.110.3 uvicorn=0.30.1 gunicorn=22.0.0 && micromamba clean --all --yes

FROM mamba as spacy

RUN micromamba install -y -n base -c conda-forge spacy=3.7.3 cupy=13.1.0 && micromamba clean --all --yes

ARG MAMBA_DOCKERFILE_ACTIVATE=1
ENV PATH=/opt/conda/bin/:$PATH

RUN python -m spacy download en_core_web_sm \
&& python -m spacy download de_core_news_sm

# RUN python -m spacy download en_core_web_trf \
#     && python -m spacy download de_core_news_trf

HEALTHCHECK CMD python -m spacy validate

ENV ANNOTATOR_NAME="duui-slc-spacy"
ENV VERSION="${VERSION}"

FROM spacy as app

WORKDIR /duui

COPY --from=base /duui /duui
COPY ./python/app/parser/*.py /duui/app/parser/

HEALTHCHECK --interval=30s --timeout=5s \
    CMD curl --silent --fail \
        -X POST \
        -H "Content-Type: application/json" \
        --data '{"text": "This is the first example. And this is the second one.", "language": "en"}' \
        localhost:9714/v1/process || exit 1

ENTRYPOINT [ "gunicorn", "wsgi:app", "-b", "0.0.0.0:9714", "-k", "uvicorn.workers.UvicornWorker", "--timeout", "3600" ]
CMD [ "-w", "1" ]