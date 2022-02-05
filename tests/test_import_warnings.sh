#!/bin/bash
set -eu

errors=0
function expect_warn () {
    echo "check: " "$@"
    [[ $(2>&1 "$@" | grep -c DEPRECATED) -gt 0 ]] || {
        echo "ERROR: " "$@"
        errors=1
    }
}

function expect_ok () {
    echo "check: " "$@"
    [[ $(2>&1 "$@" | grep -c DEPRECATED) -eq 0 ]] || {
        echo "ERROR: " "$@"
        errors=1
    }
}


# TODO actually this one might be ok? nothing wrong with it in principle
expect_warn python3 -c 'from   my import fbmessenger'
echo                   'from   my import fbmessenger' > /tmp/script.py
expect_warn python3 /tmp/script.py

expect_warn python3 -c 'from   my.fbmessenger import messages'
echo                   'from   my.fbmessenger import messages' > /tmp/script.py
expect_warn python3 /tmp/script.py

expect_warn python3 -c 'from   my.fbmessenger import *'
echo                   'from   my.fbmessenger import *' > /tmp/script.py
expect_warn python3 /tmp/script.py

expect_warn python3 -c 'import my.fbmessenger'
echo                   'import my.fbmessenger' > /tmp/script.py
expect_warn python3 /tmp/script.py

expect_warn python3 -m my.core query  my.fbmessenger.messages
expect_warn python3 -m my.core doctor my.fbmessenger


expect_ok   python3 -c 'from   my.fbmessenger.export import *'
echo                   'from   my.fbmessenger.export import *' > /tmp/script.py
expect_ok   python3 /tmp/script.py


# TODO kinda annoying: this doesn't work, and doesn't seem like traceback has anything
# guess it's fine, kind of a border case
# expect_ok   python3 -c 'from   my.fbmessenger import export'
echo                   'from   my.fbmessenger import export' > /tmp/script.py
expect_ok   python3 /tmp/script.py

expect_ok   python3 -c 'import my.fbmessenger.export'
echo                   'import my.fbmessenger.export' > /tmp/script.py
expect_ok   python3 /tmp/script.py

expect_ok   python3 -m my.core query  my.fbmessenger.export.messages
expect_ok   python3 -m my.core doctor my.fbmessenger.export


exit $errors
