ARG VERSION="1.7.1"
FROM python:3.13.4 AS pandas
RUN pip install --no-cache-dir pandas tqdm

FROM alpine:latest AS backbone_dl

ARG BACKBONE_VERSION="2023-08-28"
ENV BACKBONE_VERSION=${BACKBONE_VERSION}
ADD https://hosted-datasets.gbif.org/datasets/backbone/$BACKBONE_VERSION/backbone.zip /workspace/data/gbif_backbone/

WORKDIR /workspace/data/gbif_backbone/
RUN unzip backbone.zip Taxon.tsv VernacularName.tsv && rm -f backbone.zip

FROM pandas AS backbone

COPY --from=backbone_dl /workspace/data/gbif_backbone/ /workspace/data/gbif_backbone/

WORKDIR /workspace/
ADD parse_dwca.py /workspace/
RUN python3 parse_dwca.py \
    --input /workspace/data/gbif_backbone/ \
    --output /workspace/resources/gbif_backbone/ \
    --taxonomic_names \
    --vernacular_names \
    --gbif

    # Add excluded words from GNFinder repository as well as those defined in `resources/filter/`
FROM alpine:latest AS filter_files

WORKDIR /workspace/filter/src/

ADD https://github.com/gnames/gnfinder.git#v1.1.10:pkg/io/dict/data/common/ /workspace/filter/src/
ADD https://github.com/gnames/gnfinder.git#v1.1.10:pkg/io/dict/data/not-in/ /workspace/filter/src/
COPY resources/filter/ /workspace/filter/src/

WORKDIR /workspace/filter/
RUN cat /workspace/filter/src/* | sort -u > /workspace/filter/filter.txt

FROM docker.texttechnologylab.org/gazetteer-rs/base:${VERSION} AS app
WORKDIR /app

COPY config.toml /app/
COPY communication_layer.lua /app/
COPY --from=backbone /workspace/resources/ /app/resources/
COPY --from=filter_files /workspace/filter/filter.txt /app/resources/filter.txt

EXPOSE 9714

ENTRYPOINT ["/app/gazetteer", "--config", "config.toml", "--address", "0.0.0.0", "--port", "9714", "--limit", "536870912"]
CMD ["--workers", "1"]
