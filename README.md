Python interface into my life.

This package deals with abstracting away various data sources and providing nice Python interface for them, also lets you define covenience functions.

This might not necessarily be convenient for you to use, perhaps it's more of a concept of how you can organize and access your personal data.
But it works for me so hopefully that would help you if you're struggling!

# Setting up
First you need to tell the package where to look for your data and external repositories, which is done though a python file named `my_configuration.py`, e.g.:
```
class paths:
    class stexport:
        repo       = /path/repos/stackexchange_export_repo
        export_dir = /path/to/backups/stackexchange

    class ghexport:
        repo       = /path/repos/github_export_repo
        export_dir = /path/to/backups/github
```

and pass the filename to the package:

```
cp with_my.example with_my

# specify path to your my_configuration.py:
vim with_my
```


# Usage example
If you run your script with `with_my` wrapper, you'd have `my` in `PYTHONPATH` which gives you access to your data from within the script.


```
with_my python3 -c 'import my.books.kobo as kobo; print(kobo.get_todos())' 
```

Also read/run [demo.py](demo.py) for a full demonstration of setting up Hypothesis.
