#!/bin/bash
set -eux
pip3 install --user "$@" -e main/
pip3 install --user "$@" -e overlay/
