#!/bin/bash

set -Eeuo pipefail

PROJ_ROOT=$(dirname $(readlink -f $0))/..
ASSETS_DIR="assets/models/sdf"

# test for decompression
TEST_DIR=table

pushd ${PROJ_ROOT}/${ASSETS_DIR}

if [ -d "$TEST_DIR" ]; then
	echo "Assets have already extracted into ${ASSETS_DIR}: Nothing to do."
	exit 0
fi

for tar_file in assets_models_*.tar.xz; do
	if [ -f "$tar_file" ]; then
		echo "Extracting $tar_file -> $ASSETS_DIR"
		tar -Jxf "$tar_file"
	fi
done

popd

echo "Extraction done! Assets are ready in ${ASSETS_DIR}"

