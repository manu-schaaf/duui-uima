FROM docker.texttechnologylab.org/onnxruntime/cuda:latest as base

FROM base as rust

RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh bash -s -- -y

WORKDIR /app/

ADD src /app/src
ADD Cargo.toml /app/Cargo.toml

ARG EXECUTABLE
ARG PORT=9714
RUN cargo build --release && mv target/release/${EXECUTABLE} /app/ && rm -rf src target Cargo.toml

CMD [ "${EXECUTABLE}", "--host", "0.0.0.0", "--port", "${PORT}" ]
