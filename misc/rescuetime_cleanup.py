# M-x run-python (raise window so it doesn't hide)
# ?? python-shell-send-defun
# C-c C-r python-shell-send-region
# shit, it isn't autoscrolling??
#    maybe add hook
#    (setq comint-move-point-for-output t) ;; https://github.com/jorgenschaefer/elpy/issues/1641#issuecomment-528355368
#
from importlib import reload
import sys

# todo function to reload hpi?
todel = [m for m in sys.modules if m.startswith('my.')]
# for m in todel: del sys.modules[m]

import my
import my.rescuetime as M

from itertools import islice, groupby
from more_itertools import ilen, bucket

print(M.dataframe())

e = M.entries()
e = list(islice(e, 0, 10))


key = lambda x: 'ERROR' if isinstance(x, Exception) else x.activity

# TODO move to errors module? how to preserve type signature?
# b = bucket(e, key=key)
# for k in b:
#     g = b[k] # meh? should maybe sort
#     print(k, ilen(g))

from collections import Counter
print(Counter(key(x) for x in e))
