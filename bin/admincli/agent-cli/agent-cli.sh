#!/bin/bash

DIR=$(cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd)
NODE=$DIR/node/linux/bin/node
MAIN_SCRIPT=$DIR/bin/agent.bundle.js
FLAGS="--expose_gc"

$NODE $FLAGS $MAIN_SCRIPT "$@"
