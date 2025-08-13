ARG GEONAMES_FST_VERSION=0.4.1
FROM docker.texttechnologylab.org/duui-geonames-fst/base:${GEONAMES_FST_VERSION} AS builder

WORKDIR /build/
RUN cargo build --release --no-default-features --features duui
RUN chmod +x /build/target/release/geonames-fst

FROM alpine:latest AS data
RUN apk --update add unzip && rm -rf /var/cache/apk/*

ARG COUNTRY="DE"

ADD https://download.geonames.org/export/dump/${COUNTRY}.zip /tmp/geonames/${COUNTRY}.zip
ADD https://download.geonames.org/export/dump/alternatenames/${COUNTRY}.zip /tmp/alternateNames/${COUNTRY}.zip

RUN mkdir -p /data/geonames/ /data/alternateNames/ && \
    unzip -d /data/geonames/ /tmp/geonames/$COUNTRY.zip $COUNTRY.txt && \
    unzip -d /data/alternateNames/ /tmp/alternateNames/$COUNTRY.zip $COUNTRY.txt && \
    stat -c %y /data/geonames/* | sort -r | head -n 1 > /data/geonames_timestamp.txt && \
    gzip -9 /data/geonames/* /data/alternateNames/*

FROM cgr.dev/chainguard/glibc-dynamic:latest AS prod
COPY --from=builder /build/target/release/geonames-fst /app/
COPY --from=data /data /app/data/
COPY src/main/resources/ /app/resources/
WORKDIR /app/

ENV RUST_LOG="info,tower_http=debug,axum::rejection=trace"

EXPOSE 9714
ENTRYPOINT ["/app/geonames-fst", "--port", "9714", "/app/data/geonames/", "--alternate", "/app/data/alternateNames/", "--timestamp", "/app/data/geonames_timestamp.txt"]
CMD ["--workers", "1"]