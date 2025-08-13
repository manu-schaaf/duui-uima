export VERSION=1.6.1
export GAZETTER_VERSION=1.6.1
export NAME=biofid-habitat

rsync -ahz --info=Progress2 sirao:/resources/nlp/gazetteer_lists/filter_de.txt resources/
rsync -ah --info=Progress2 sirao:/resources/nlp/gazetteer_lists/biofid_habitat/ resources/

docker build --build-arg VERSION="${GAZETTER_VERSION}" -t gazetteer-rs/${NAME}:${VERSION} .
docker image tag gazetteer-rs/${NAME}:${VERSION} docker.texttechnologylab.org/gazetteer-rs/${NAME}:latest
docker image tag gazetteer-rs/${NAME}:${VERSION} docker.texttechnologylab.org/gazetteer-rs/${NAME}:${VERSION}
docker push docker.texttechnologylab.org/gazetteer-rs/${NAME}:latest
docker push docker.texttechnologylab.org/gazetteer-rs/${NAME}:${VERSION}
