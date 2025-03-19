FROM rust:latest AS builder

ARG VERSION="latest"

WORKDIR /app/src/
RUN git clone --branch "$VERSION" "https://github.com/texttechnologylab/gazetteer-rs/" /app/src/
RUN cargo build --release --no-default-features
RUN chmod +x /app/src/target/release/gazetteer

FROM cgr.dev/chainguard/glibc-dynamic:latest AS prod
COPY --from=builder /app/src/target/release/gazetteer /app/
WORKDIR /app/
