#!/bin/bash

set -Eeuo pipefail

cd $(dirname $(readlink -f $0))

IMAGE=voxelsky/ros-humble-desktop-classic:v0.0.2
# 备用镜像（阿里云私有镜像仓库）
FALLBACK_IMAGE=crpi-ez0mp20rl5djukrk.cn-shanghai.personal.cr.aliyuncs.com/voxelsky/ros-humble-desktop-classic:v0.0.2
CONT=ros2-dev

if ! docker image inspect "$IMAGE" >/dev/null 2>&1; then
    echo "Image $IMAGE not found locally, using fallback: $FALLBACK_IMAGE"
    IMAGE="$FALLBACK_IMAGE"
fi

set +e
IS_RUN=$(docker container ls -a | grep $CONT)
set -e

if [ -n "$IS_RUN" ]; then
	./ros-desktop.sh \
		--ros-dist humble \
		--image $IMAGE \
		--name $CONT restart
else
	./ros-desktop.sh \
		--ros-dist humble \
		--image $IMAGE \
		--name $CONT \
		-- --net=host -v $PWD:/root/workspace
fi

