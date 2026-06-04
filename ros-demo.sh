#!/bin/bash

set -Eeuo pipefail

cd $(dirname $(readlink -f $0))

IMAGE=voxelsky/ohos-rsim-nav2-demo:v0.0.1
# 备用镜像（阿里云私有镜像仓库）
FALLBACK_IMAGE=crpi-ez0mp20rl5djukrk.cn-shanghai.personal.cr.aliyuncs.com/voxelsky/ohos-rsim-nav2-demo:v0.0.1
CONT=ros2-demo

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
		-- --net=host -v $PWD:/root/workspace --gpus all
fi

