#!/usr/bin/env bash
# stop Netboot Studio

function bail() {
  echo "Something went wrong: $1"
  exit 1
}

git pull || bail "failed to git pull"
./deploy.sh || bail "failed to deploy"
./monitor.sh
