#!/bin/bash

set -Eeuo pipefail

cd $(dirname $(readlink -f $0))

# sed 's/^export ROS_DISTRO=.*/export ROS_DISTRO=humble/' noros.bashrc.in > noros.bashrc
sed 's/^export ROS_DISTRO=.*/export ROS_DISTRO=humble/' ros.bashrc.in > ros.bashrc

docker build -t voxelsky/ros-humble-desktop-classic:v0.0.2 -f Dockerfile.ros.humble.classic .

