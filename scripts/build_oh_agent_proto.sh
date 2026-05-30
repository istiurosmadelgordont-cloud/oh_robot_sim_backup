#!/bin/bash

set -Eeuo pipefail

SCRIPT_DIR=$(dirname $(readlink -f $0))
PROJ_ROOT=$SCRIPT_DIR/..
OH_AGENT_PROTO_ROOT=$PROJ_ROOT/oh_agent/oh_agent

GRPC_GEN_ROOT=$PROJ_ROOT/control_stubs
GPRC_PROTOs=${GRPC_GEN_ROOT}/control_stubs/*.proto

python3 -m grpc_tools.protoc \
    -I${GRPC_GEN_ROOT} \
    --python_out=${OH_AGENT_PROTO_ROOT} \
    --grpc_python_out=${OH_AGENT_PROTO_ROOT} \
    --pyi_out=${OH_AGENT_PROTO_ROOT} \
    ${GPRC_PROTOs}

