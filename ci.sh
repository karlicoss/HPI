#!/bin/bash

cd "$(this_dir)" || exit

. ~/bash_ci

ci_run mypy calls
ci_run pylint -E calls

ci_report_errors
