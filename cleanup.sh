#!/usr/bin/env bash
# cleanup Netboot Studio docker images

function bail() {
  echo "Something went wrong: $1"
  exit 1
}

docker system prune --volumes -f || bail "failed to prune docker system"

echo "success"
