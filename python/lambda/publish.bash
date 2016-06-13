#!/bin/env bash

set -e
set -x

#pip install -r requirements.pip -t vendor/

lambda-uploader -p ../lambda --requirements requirements.pip
