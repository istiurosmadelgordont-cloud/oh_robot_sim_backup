#!/bin/bash

set -Eeuo pipefail

PROJ_ROOT=$(dirname $(readlink -f $0))/..
ASSETS_DIR="assets/models/sdf"

pushd ${PROJ_ROOT}/${ASSETS_DIR}

for dir in "$PWD"/*/; do
  dir_name=$(basename "$dir")
  tar_file="assets_models_${dir_name}.tar.xz"
  
  # if compress file doesn't exist / dir updated (modify time)
  if [ ! -f "$tar_file" ] || [ "$dir" -nt "$tar_file" ]; then
    echo "Compressing $dir -> $tar_file"
    tar -Jcf "$tar_file" "$dir_name"
  fi
done

popd

echo "Compression done! Track these files: ${PROJ_ROOT}/${ASSETS_DIR}/assets_models_*.tar.gz"

