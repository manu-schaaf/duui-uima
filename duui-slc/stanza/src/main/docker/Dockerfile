ARG VERSION
ARG CUDA_NAME="cu121"
ARG CUDA_VERSION="12.1.1"

FROM docker.texttechnologylab.org/duui-slc-base/${CUDA_NAME}:${VERSION} as base

FROM ghcr.io/mamba-org/micromamba:jammy-cuda-${CUDA_VERSION} as mamba

RUN micromamba install -y -n base -c conda-forge python=3.11 fastapi=0.110.3 uvicorn=0.30.1 gunicorn=22.0.0 && micromamba clean --all --yes
RUN micromamba install -y -n base pytorch pytorch-cuda=${CUDA_VERSION%.*} -c pytorch -c nvidia -c conda-forge && micromamba clean --all --yes

FROM mamba as stanza

ENV ANNOTATOR_NAME="duui-slc-stanza"
ENV VERSION="${VERSION}"

RUN micromamba install -y -n base -c conda-forge stanza-with-transformers=1.5.1 && micromamba clean --all --yes

ARG MAMBA_DOCKERFILE_ACTIVATE=1
ENV PATH=/opt/conda/bin/:$PATH

RUN python -c "import stanza; stanza.download('en'); stanza.download('de'); stanza.download('fr'); "

FROM stanza as app

WORKDIR /duui

COPY --from=base /duui /duui
COPY ./python/app/parser/*.py /duui/app/parser/


# HEALTHCHECK --interval=30s --timeout=5s \
#     CMD curl --silent --fail \
#         -X POST \
#         -H "Content-Type: application/json" \
#         --data '{"text": "Barack Obama was born in Hawaii.", "language": "en", "sentences": [{"begin": 0, "end": 32}]}' \
#         localhost:9714/v1/process || exit 1

ENTRYPOINT [ "gunicorn", "wsgi:app", "-b", "0.0.0.0:9714", "-k", "uvicorn.workers.UvicornWorker", "--timeout", "3600" ]
CMD [ "-w", "1" ]
