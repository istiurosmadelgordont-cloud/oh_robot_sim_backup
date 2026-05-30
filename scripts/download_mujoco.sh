#!/bin/bash

set -Eeuo pipefail

PROJ_ROOT=$(dirname $(readlink -f $0))/..

pushd ${PROJ_ROOT}

wget https://github.com/google-deepmind/mujoco/releases/download/3.3.4/mujoco-3.3.4-linux-x86_64.tar.gz                                                                                       
tar -zxpvf mujoco-3.3.4-linux-x86_64.tar.gz                                                                                                                                                   
mv mujoco-3.3.4 3.3.4                                                                                                                                                                         
mkdir mujoco && mv 3.3.4 mujoco                                                                                                                                                               
rm mujoco-3.3.4-linux-x86_64.tar.gz

popd
