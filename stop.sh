#!/usr/bin/env bash
# stop Netboot Studio

function bail() {
  echo "Something went wrong: $1"
  exit 1
}

echo "Stopping and removing any running containers..."
docker-compose stop || bail "failed to stop containers, have you logged out and back in since first_time_setup.sh? "
docker-compose rm -f || bail "failed to remove containers"
echo "success"
exit 0
