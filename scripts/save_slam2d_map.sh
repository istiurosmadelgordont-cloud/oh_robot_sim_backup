#!/bin/bash

set -Eeuo pipefail

cd $(dirname $(readlink -f $0))

MAP_NAME=${1:-default_map}

ros2 run nav2_map_server map_saver_cli -f $PWD/assets/maps/slam2d/$MAP_NAME
