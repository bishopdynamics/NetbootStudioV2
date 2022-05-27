#!/usr/bin/env bash

# Make documentation

echo "building docs"

source venv/bin/activate
pushd docs || exit 1

make html || exit 1
#sphinx-build -b rinoh source build/rinoh || exit 1

cp -r build/html . || exit 1
#cp -r build/rinoh/netbootstudio.pdf . || exit 1
