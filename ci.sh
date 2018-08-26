#!/bin/bash

cd "$(this_dir)" || exit

. ~/bash_ci

ci_run mypy photos
ci_run pylint -E photos

ci_report_errors
