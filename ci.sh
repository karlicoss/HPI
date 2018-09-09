#!/bin/bash

cd "$(this_dir)" || exit

. ~/bash_ci

ci_run mypy foursquare
ci_run pylint -E foursquare

ci_report_errors
