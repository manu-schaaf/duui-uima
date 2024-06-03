ARG BASE_VERSION
ARG CUDA_NAME="cu124"
FROM docker.texttechnologylab.org/duui-slc-base/${CUDA_VERSION}:${BASE_VERSION}

RUN micromamba install -y -n base -c conda-forge stanza=1.5.1 && micromamba clean --all --yes

RUN python -c "import stanza; stanza.download('en'); stanza.download('de'); stanza.download('fr'); "

WORKDIR /duui

COPY ./python/app/specific/ /duui/app/specific/

ENTRYPOINT [ "gunicorn", "wsgi:app", "-b", "0.0.0.0:9714", "-k", "uvicorn.workers.UvicornWorker" ]
CMD [ "-w", "1" ]