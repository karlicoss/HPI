#!/bin/bash

cd "$(this_dir)" || exit

. ~/bash_ci

ci_run mypy goodreads
ci_run pylint -E goodreads

ci_report_errors
