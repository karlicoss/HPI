"""
EXPERIMENTAL! use with caution
Manages 'global' ProcessPoolExecutor which is 'managed' by HPI itself, and
can be passed down to DALs to speed up data processing.

The reason to have it managed by HPI is because we don't want DALs instantiate pools
themselves -- they can't cooperate and it would be hard/infeasible to control
how many cores we want to dedicate to the DAL.

Enabled by the env variable, specifying how many cores to dedicate
e.g. "HPI_CPU_POOL=4 hpi query ..."
"""

from __future__ import annotations

import os
from concurrent.futures import ProcessPoolExecutor
from typing import cast

_NOT_SET = cast(ProcessPoolExecutor, object())
_INSTANCE: ProcessPoolExecutor | None = _NOT_SET


def get_cpu_pool() -> ProcessPoolExecutor | None:
    global _INSTANCE
    if _INSTANCE is _NOT_SET:
        use_cpu_pool = os.environ.get('HPI_CPU_POOL')
        if use_cpu_pool is None or int(use_cpu_pool) == 0:
            _INSTANCE = None
        else:
            # NOTE: this won't be cleaned up properly, but I guess it's fine?
            # since this it's basically a singleton for the whole process
            # , and will be destroyed when python exists
            _INSTANCE = ProcessPoolExecutor(max_workers=int(use_cpu_pool))
    return _INSTANCE
