#!/usr/bin/env bash
# Create virtualenv with correct python version and install requirements
#  takes one flag, the name for virtualenv

#    This file is part of Netboot Studio, a system for managing netboot clients
#    Copyright (C) 2020-2023 James Bishop (james@bishopdynamics.com)

ENV_FOLDER="venv"
PYTHON_VERSION="python3"

command -v "$PYTHON_VERSION" || {
	echo "$PYTHON_VERSION is required, but was not found"
	exit 1
}

if [ -d "${ENV_FOLDER}" ]; then
  echo "removing previous instance of ${ENV_FOLDER}"
  rm -rf "${ENV_FOLDER}" || {
  	echo "failed to remove previous env ${ENV_FOLDER}/ please do so manually"
  	exit 1
  }
fi

echo "setting up ${ENV_FOLDER}/"
"$PYTHON_VERSION" -m virtualenv "${ENV_FOLDER}" || {
	echo "failed to create env ${ENV_FOLDER}, probably missing $PYTHON_VERSION virtualenv module"
	echo "going to try installing that now"
	"$PYTHON_VERSION" -m pip install virtualenv || {
	  echo "ugh, that failed"
	  exit 1
	}
	echo "trying again to set up ${ENV_FOLDER}/"
	"$PYTHON_VERSION" -m virtualenv "${ENV_FOLDER}" || {
	  echo "failed to create env ${ENV_FOLDER}, probably missing $PYTHON_VERSION virtualenv module"
	  echo "we already tried to install it for you, so there may be something else wrong"
	  exit 1
	}
}

echo "installing requirements.txt"
source "${ENV_FOLDER}/bin/activate" || {
	echo "failed to activate env ${ENV_FOLDER}, weird"
	exit 1
}
# once inside the env, pip & python are local versions
pip install --upgrade pip || {
  echo "failed to upgrade pip? huh..."
  exit 1
}
pip install -r requirements.txt || {
  echo "failed to install packages from requirements.txt"
  deactivate
  exit 1
}


deactivate

echo "done"
