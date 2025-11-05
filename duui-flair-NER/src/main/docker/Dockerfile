FROM nvidia/cuda:12.8.1-cudnn-runtime-ubi8 AS base

RUN dnf install -y python3.12 python3.12-pip && python3.12 -m pip install -U pip setuptools wheel

WORKDIR /app/
RUN python3.12 -m venv venv && ./venv/bin/python -m pip install -U flair 'fastapi[standard]' uvicorn pydantic_settings 'transformers[hf_xet]'

# Pre-load Flair taggers
ENV FLAIR_CACHE_ROOT="/app/cache"
RUN ./venv/bin/python -c "\
from flair.models import SequenceTagger; \
SequenceTagger.load('flair/ner-german-large'); \
SequenceTagger.load('flair/ner-english-large');"

COPY ./src/main/lua/communication_layer.lua ./communication_layer.lua
COPY ./src/main/resources/dkpro-core-types.xml ./dkpro-core-types.xml
COPY ./src/main/resources/logging.yaml ./logging.yaml
COPY ./src/main/python/wsgi.py ./wsgi.py

ARG MODEL_CACHE_SIZE=1
ENV MODEL_CACHE_SIZE=$MODEL_CACHE_SIZE

ARG FLAIR_BATCH_SIZE=128
ENV FLAIR_BATCH_SIZE=$FLAIR_BATCH_SIZE

ENTRYPOINT ["./venv/bin/uvicorn", "wsgi:app", "--host", "0.0.0.0", "--port" ,"9714", "--log-config", "logging.yaml", "--use-colors"]
CMD ["--workers", "1"]
