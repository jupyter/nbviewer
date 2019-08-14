NAMESPACE=dmmmd
APP=nbviewer

# --link dockerhost assumes that https://github.com/qoomon/docker-host is running
#  docker run --name 'dockerhost' \
#  --cap-add=NET_ADMIN --cap-add=NET_RAW \
#  --restart on-failure \
# qoomon/docker-host

build:
	docker build --no-cache -t ${NAMESPACE}/${APP} .
run:
	docker run --name=${APP} --detach=false --link dockerhost -p 5000:5000 ${NAMESPACE}/${APP}
clean:
	docker stop ${APP} && docker rm ${APP}
reset: clean
	docker rmi ${NAMESPACE}/${APP}
interactive:
	docker run --rm --interactive --tty --name=${APP} ${NAMESPACE}/${APP} bash
push:
	docker push ${NAMESPACE}/${APP}
