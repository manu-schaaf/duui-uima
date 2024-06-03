ARG BASE_VERSION
ARG CUDA_NAME="cu124"
FROM docker.texttechnologylab.org/duui-slc-base/${CUDA_NAME}:${BASE_VERSION}

RUN micromamba install -y -n base -c conda-forge spacy=3.7.3 cupy=13.1.0 && micromamba clean --all --yes

RUN python -m spacy download en_core_web_sm \
    && python -m spacy download de_core_news_sm

# RUN python -m spacy download en_core_web_trf \
#     && python -m spacy download de_core_news_trf

HEALTHCHECK CMD python -m spacy validate

WORKDIR /duui

COPY ./python/app/specific/ /duui/app/specific/

ENTRYPOINT [ "gunicorn", "wsgi:app", "-b", "0.0.0.0:9714", "-k", "uvicorn.workers.UvicornWorker" ]
CMD [ "-w", "1" ]