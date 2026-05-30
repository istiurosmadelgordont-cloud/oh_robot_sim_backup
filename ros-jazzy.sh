#!/bin/bash

set -Eeuo pipefail

cd $(dirname $(readlink -f $0))

#IMAGE=ros-humble-base-desktop:latest
IMAGE=ros-jazzy-gzb-desktop:latest
CONT=ros-jazzy-test

set +e
IS_RUN=$(docker container ls -a | grep $CONT)
set -e

if [ -n "$IS_RUN" ]; then
	./ros-desktop.sh \
		--ros-dist jazzy \
		--image $IMAGE \
		--name $CONT restart
else
	./ros-desktop.sh \
		--ros-dist jazzy \
		--image $IMAGE \
		--name $CONT \
		--ssh-port 22 \
		--grpc-port 50051 \
		-- -p 8001:8001 -p 8002:8002 -v $PWD:/root/workspace
fi

