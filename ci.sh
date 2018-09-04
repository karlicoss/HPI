#!/bin/bash

cd "$(this_dir)" || exit

. ~/bash_ci

ci_run mypy reddit
ci_run pylint -E reddit

ci_report_errors
