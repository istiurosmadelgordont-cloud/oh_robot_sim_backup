#!/bin/bash

set -Eeuo pipefail
# set -x

cd $(dirname $(readlink -f $0))

IS_WSL=false
IS_WINDOWS=false

USE_XAUTH=false
USE_WAYLAND=false

WAYLAND_SOCKET=""
XDG_RUNTIME_DIR_HOST="${XDG_RUNTIME_DIR:-/run/user/$(id -u)}"

if grep -qi microsoft /proc/version 2>/dev/null; then
    IS_WSL=true
    IS_WINDOWS=true
elif [[ "$OSTYPE" == "msys"* || "$OSTYPE" == "cygwin"* ]]; then
    IS_WINDOWS=true
fi

ROS_DISTRO=""
SSH_PORT=10022
GRPC_PORT=50052

SPEC_IMAGE=""
SPEC_CONTAINER_NAME=""
DOCKER_EXTRA_ARGS=""
COMMAND=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --ros-dist)
            ROS_DISTRO="$2"
            shift 2
            ;;
        --image)
            SPEC_IMAGE="$2"
            shift 2
            ;;
        --name)
            SPEC_CONTAINER_NAME="$2"
            shift 2
            ;;
        --ssh-port)
            SSH_PORT="$2"
            shift 2
            ;;
        --grpc-port)
            GRPC_PORT="$2"
            shift 2
            ;;
        --help)
            echo "Usage: $0 --ros-dist <name> --image <ros_image> [--name str] [--ssh-port port] [--grpc-port port] [--help] [restart] [-- extra docker args]"
            exit 0
            ;;
        --)
            shift
            DOCKER_EXTRA_ARGS+=("$@")
            break
            ;;
        restart)
            COMMAND="restart"
            shift
            ;;
        *)
            echo "Error: unknown argument '$1'"
            exit 1
            ;;
    esac
done

if [ -z "$ROS_DISTRO" ]; then
	echo "Error: specify ros distribution with --ros-dist <name>"
	exit 0
fi
XAUTH=/tmp/.docker.ros.${ROS_DISTRO}.desktop.xauth
if [ -z "$SPEC_IMAGE" ]; then
	echo "Error: specify at least one image"
	exit 1
fi
IMAGE_NAME=${SPEC_IMAGE}
CONT_NAME=${SPEC_CONTAINER_NAME:-ros-${ROS_DISTRO}-desktop-container}

# remove empty elements in extra args
declare -a DOCKER_EXTRA_ARGS_CLEAN=()
for arg in "${DOCKER_EXTRA_ARGS[@]}"; do
    if [[ -n "$arg" ]]; then
        DOCKER_EXTRA_ARGS_CLEAN+=("$arg")
    fi
done

# Add GPU device only if not in WSL
if [ "$IS_WSL" = false ] && [ "$IS_WINDOWS" = false ]; then
    DOCKER_EXTRA_ARGS_CLEAN+=("--device" "/dev/dri")
fi

# DOCKER_EXTRA_ARGS=("${DOCKER_EXTRA_ARGS[@]/''/}")

echo -e "\n------ Configurations ------"
echo -e "Command: ${COMMAND:-Default Start}"
echo -e "ROS Distro: $ROS_DISTRO"
echo -e "SSH Port: $SSH_PORT"
echo -e "GRPC Port: $GRPC_PORT"
echo -e "Image Name: $IMAGE_NAME"
echo -e "Container Name: $CONT_NAME"
echo -e "Docker Extra Args: ${DOCKER_EXTRA_ARGS_CLEAN[@]}"
echo -e "----------------------------\n"

if [ "$IS_WINDOWS" = true ]; then
    # WSL2: always use WSLg X11 socket + GPU driver libs
    DISPLAY=${DISPLAY:-:0}
    USE_XAUTH=false
    USE_WAYLAND=true
else
    if [ -n "${WAYLAND_DISPLAY:-}" ]; then
        USE_WAYLAND=true
        USE_XAUTH=false
	# Keep DISPLAY for XWayland clients
	DISPLAY="${DISPLAY:-:0}"
    else
        USE_WAYLAND=false
        USE_XAUTH=true
    fi
fi

if [ "$USE_XAUTH" = true ]; then
    touch $XAUTH
    xauth nlist $DISPLAY | sed -e 's/^..../ffff/' | xauth -f $XAUTH nmerge -
fi

if [ "$COMMAND" = "restart" ]; then
    echo "Restarting container $CONT_NAME..."
    docker restart $CONT_NAME
    docker exec -it $CONT_NAME bash
else
    docker run -it \
	$( [ "$USE_WAYLAND" = true ] && echo "\
	-e WAYLAND_DISPLAY=$WAYLAND_DISPLAY \
	-e XDG_RUNTIME_DIR=/run/user/$(id -u) \
	-e DISPLAY=$DISPLAY \
    -v /mnt/wslg/.X11-unix:/tmp/.X11-unix \
    -v /mnt/wslg:/mnt/wslg \
    -v /usr/lib/wsl:/usr/lib/wsl \
    -e LD_LIBRARY_PATH=/usr/lib/wsl/lib \
	-v $XDG_RUNTIME_DIR_HOST:/run/user/$(id -u) \
	" ) \
	$( [ "$USE_WAYLAND" = false ] && echo "\
	-e DISPLAY=$DISPLAY \
	-e QT_X11_NO_MITSHM=1 \
	-v /tmp/.X11-unix:/tmp/.X11-unix \
	" ) \
	-p $SSH_PORT:22 \
	-p $GRPC_PORT:50051 \
    -e NVIDIA_DRIVER_CAPABILITIES=all \
    -e QT_X11_NO_MITSHM=1 \
	"${DOCKER_EXTRA_ARGS_CLEAN[@]}" \
        --name $CONT_NAME \
        $IMAGE_NAME \
        bash -c "echo -e \"\
$( [ "$USE_WAYLAND" = true ] && echo 'export WAYLAND_DISPLAY='"$WAYLAND_DISPLAY"';' )\
$( [ "$USE_WAYLAND" = true ] && echo 'export XDG_RUNTIME_DIR=/run/user/'"$(id -u)"';' )\
$( [ "$USE_WAYLAND" = true ] && echo 'export QT_QPA_PLATFORM=\"xcb;wayland;\";' )\
$( [ "$USE_WAYLAND" = true ] && echo 'export GDK_BACKEND=wayland,x11;' )\
$( [ "$USE_WAYLAND" = true ] && echo 'export MOZ_ENABLE_WAYLAND=1;' )\
\nexport DISPLAY=$DISPLAY;\
\nexport MUJOCO_VER=3.3.4;\
\nexport MUJOCO_DIR=/root/workspace/mujoco/\\\${MUJOCO_VER};\
\nexport PATH=\\\${PATH}:/root/workspace/blender-app:\\\${MUJOCO_DIR}/bin;\
\nexport RMW_IMPLEMENTATION=rmw_cyclonedds_cpp;\
\n\" >> /root/.bashrc_ros && /usr/sbin/sshd && /usr/bin/bash --rcfile /root/.bashrc"


fi

[ "$USE_XAUTH" = true ] && rm -f "$XAUTH"

