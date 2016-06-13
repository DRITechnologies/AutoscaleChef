#!/bin/env bash

set -e
set -x

# constants
FUNCTION_NAME='ChefAutoScaleNode'

# package function
# node-lambda package --functionName $FUNCTION_NAME --packageDirectory .

# upload function
node-lambda deploy \
        --region us-west-2 \
        --functionName $FUNCTION_NAME \
        --handler function.handler \
        --memorySize 128 \
        --timeout 30 \
        --description 'Creates and deletes chef objects according to scale events' \
        --runtime nodejs4.3
