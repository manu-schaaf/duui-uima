FROM docker.io/pytorch/libtorch-cxx11-builder:cuda118 as base

FROM base as rust

RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh bash -s -- -y

WORKDIR /app/

ARG PORT=9714

ARG MAX_PAYLOAD_SIZE=16777215
ENV MAX_PAYLOAD_SIZE=${MAX_PAYLOAD_SIZE}

ARG RUST_LOG=info
ENV RUST_LOG=${RUST_LOG}

ADD src /app/src
ADD Cargo.toml /app/Cargo.toml

RUN cargo build --release && mv target/release/duui-ner-rust_bert /app/wsgi && rm -rf src target Cargo.toml

ADD communication_layer.lua /app/communication_layer.lua

CMD [ "${EXECUTABLE}", "--host", "0.0.0.0", "--port", "${PORT}" ]
