#!/bin/bash

cd "$(this_dir)" || exit

. ~/bash_ci

ci_run python3.6 test.py

ci_report_errors
