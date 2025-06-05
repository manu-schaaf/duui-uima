FROM nvcr.io/nvidia/pytorch:25.05-py3 AS base

WORKDIR /workspace/app/
RUN python3 -m pip install -U 'fastapi[standard]' uvicorn pydantic_settings 'spacy[cuda12x,transformers,lookups]' 'transformers[hf_xet]'

RUN python3 -m spacy download ca_core_news_sm && \
    python3 -m spacy download zh_core_web_sm && \
    python3 -m spacy download hr_core_news_sm && \
    python3 -m spacy download da_core_news_sm && \
    python3 -m spacy download nl_core_news_sm && \
    python3 -m spacy download en_core_web_sm && \
    python3 -m spacy download fi_core_news_sm && \
    python3 -m spacy download fr_core_news_sm && \
    python3 -m spacy download de_core_news_sm && \
    python3 -m spacy download el_core_news_sm && \
    python3 -m spacy download it_core_news_sm && \
    python3 -m spacy download ja_core_news_sm && \
    python3 -m spacy download ko_core_news_sm && \
    python3 -m spacy download lt_core_news_sm && \
    python3 -m spacy download mk_core_news_sm && \
    python3 -m spacy download nb_core_news_sm && \
    python3 -m spacy download pl_core_news_sm && \
    python3 -m spacy download pt_core_news_sm && \
    python3 -m spacy download ro_core_news_sm && \
    python3 -m spacy download ru_core_news_sm && \
    python3 -m spacy download sl_core_news_sm && \
    python3 -m spacy download es_core_news_sm && \
    python3 -m spacy download sv_core_news_sm && \
    python3 -m spacy download uk_core_news_sm && \
    python3 -m spacy download xx_sent_ud_sm

COPY src/ /workspace/app/

ARG COMPONENT_NAME="duui-spacy-eos"
ENV COMPONENT_NAME=${COMPONENT_NAME}

ARG VERSION="0.1.0"
ENV COMPONENT_VERSION=${VERSION}

ARG SPACY_LANGUAGE="xx"
ENV SPACY_LANGUAGE=${SPACY_LANGUAGE}

ENTRYPOINT ["uvicorn", "duui:app", "--host", "0.0.0.0", "--port" ,"9714", "--use-colors"]
CMD ["--workers", "1"]