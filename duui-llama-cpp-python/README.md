# llama-cpp-python

DUUI components for [llama-cpp-python](https://github.com/abetlen/llama-cpp-python).

## Base Image

The base image in [`Dockerfile.base`](src/main/docker/Dockerfile.base) is derived from the [cuda_simple/Dockerfile](https://github.com/abetlen/llama-cpp-python/blob/22917989003c5e67623d54ab45affa1e0e475410/docker/cuda_simple/Dockerfile) in the llama-cpp-python repository.

## DUUI v1 Image

The [`Dockerfile`](src/main/docker/Dockerfile) then builds on this image to implement the basic logic for the DUUI interface v1.

## Model Images

### `huggingface-hub`

The auxillary image defined in [`Dockerfile.hf`](src/main/docker/Dockerfile.hf) is available as `docker.texttechnologylab.org/llm/hf:latest`.
Use it to fetch the model files directly from the HuggingFace Hub, if applicable.

Under the hood, it's just a slim Python image with the `huggingface-hub` package installed.

```Dockerfile
FROM python:3.12-slim

RUN python3 -m pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir --upgrade huggingface-hub
```

We can then use the `huggingface-hub` CLI to download models:

```shell
huggingface-cli download TheBloke/TinyLlama-1.1B-Chat-v1.0-GGUF tinyllama-1.1b-chat-v1.0.Q2_K.gguf
```

### Layered Build

Using the `docker.texttechnologylab.org/llm/hf:latest` image, we can utilize layered builds to add a fetched model to a DUUI v1 image.

#### Example

```Dockerfile
# build layer for fetching the model that may be reused
FROM docker.texttechnologylab.org/llm/hf:latest as fetch

RUN huggingface-cli download TheBloke/TinyLlama-1.1B-Chat-v1.0-GGUF tinyllama-1.1b-chat-v1.0.Q2_K.gguf

# build layer for the actual component
FROM docker.texttechnologylab.org/llm/llama-cpp-python:latest as component
COPY --from=fetch /root/.cache/huggingface/hub /root/.cache/huggingface/hub

WORKDIR /app/
COPY ./src/main/resources/config.json /app/

CMD gunicorn wsgi:app -b ${HOST}:${PORT} -k uvicorn.workers.UvicornWorker
```

The `fetch` layer does not need to be rebuild, even when the `docker.texttechnologylab.org/llm/llama-cpp-python` is updated and we need to rebuild the image.
The example image above is available as `docker.texttechnologylab.org/llm/llama-cpp-python/tinyllama-1.1b:latest`.