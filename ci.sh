#!/bin/bash

cd "$(this_dir)" || exit

. ~/bash_ci

ci_run mypy location
ci_run pylint -E location

ci_report_errors
