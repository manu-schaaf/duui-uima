FROM nvcr.io/nvidia/pytorch:25.05-py3 AS base

WORKDIR /workspace/app/
RUN python3 -m pip install -U 'fastapi[standard]' uvicorn pydantic_settings 'spacy[cuda12x,transformers,lookups]' 'transformers[hf_xet]'

RUN python3 -m spacy download de_core_news_sm && \
    python3 -m spacy download de_core_news_md && \
    python3 -m spacy download de_core_news_lg && \
    python3 -m spacy download de_dep_news_trf

COPY src/main/ /workspace/app/

ARG COMPONENT_NAME="duui-spacy-lua-process"
ENV COMPONENT_NAME=${COMPONENT_NAME}

ARG VERSION="0.2.0"
ENV COMPONENT_VERSION=${VERSION}

ARG SPACY_LANGUAGE="de"
ENV SPACY_LANGUAGE=${SPACY_LANGUAGE}

ARG SPACY_MODEL_SIZE="trf"
ENV SPACY_MODEL_SIZE=${SPACY_MODEL_SIZE}

ARG SPACY_BATCH_SIZE=32
ENV SPACY_BATCH_SIZE=${SPACY_BATCH_SIZE}

ARG MAX_LOADED_MODELS=1
ENV MAX_LOADED_MODELS=${MAX_LOADED_MODELS}

ARG REQUEST_BATCH_SIZE=1024
ENV REQUEST_BATCH_SIZE=${REQUEST_BATCH_SIZE}

ENTRYPOINT ["uvicorn", "wsgi:app", "--host", "0.0.0.0", "--port" ,"9714", "--use-colors"]
CMD ["--workers", "1"]