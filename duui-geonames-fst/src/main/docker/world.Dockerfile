ARG GEONAMES_FST_VERSION=0.4.0
FROM docker.texttechnologylab.org/duui-geonames-fst/base:${GEONAMES_FST_VERSION} AS builder

WORKDIR /build/
RUN cargo build --release --no-default-features --features duui
RUN chmod +x /build/target/release/geonames-fst

FROM alpine:latest AS data
RUN apk --update add unzip && rm -rf /var/cache/apk/*

ADD https://download.geonames.org/export/dump/allCountries.zip /data/geonames/
ADD https://download.geonames.org/export/dump/alternateNames.zip /data/alternateNames/

WORKDIR /data/geonames
RUN unzip allCountries.zip && rm -f allCountries.zip readme.txt

WORKDIR /data/alternateNames
RUN unzip alternateNames.zip && rm -f alternateNames.zip readme.txt iso-languagecodes.txt

FROM cgr.dev/chainguard/glibc-dynamic:latest AS prod
COPY --from=builder /build/target/release/geonames-fst /app/
COPY --from=data /data /app/data/
COPY src/main/resources/ /app/resources/
WORKDIR /app/

ENV RUST_LOG="info,tower_http=debug,axum::rejection=trace"

EXPOSE 9714
ENTRYPOINT ["/app/geonames-fst", "--port", "9714", "/app/data/geonames/", "--alternate", "/app/data/alternateNames/"]
CMD ["--workers", "1"]