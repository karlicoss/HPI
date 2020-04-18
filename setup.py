#!/usr/bin/env python3
# see https://github.com/karlicoss/pymplate for up-to-date reference

from setuptools import setup, find_packages # type: ignore

INSTALL_REQUIRES = [
    'appdirs',
    'pytz', # even though it's not needed by the core, it's so common anyway...
]


def subpackages():
    # fucking hell. there must be a better way...
    # TODO FIXME add a test that it install everything I need..
    from os import sep
    from pathlib import Path
    root = Path(__file__).parent
    sources = root / 'my'
    subs = [
        str(p.relative_to(root)).replace(sep, '.')
        for p in sources.glob('*') if p.is_dir() and len(list(p.rglob('*.py'))) > 0
    ]
    return list(sorted(subs))


def main():
    pkg = 'my'
    setup(
        name='HPI', # NOTE: 'my' is taken for PyPi already, and makes discovering the project impossible. so we're using HPI
        use_scm_version={
            'version_scheme': 'python-simplified-semver',
            'local_scheme': 'dirty-tag',
        },
        setup_requires=['setuptools_scm'],

        zip_safe=False,

        # eh. find_packages doesn't find anything
        # find_namespace_packages can't find isngle file namspace packages (like my/common.py)
        packages=[pkg, *subpackages()],
        package_data={
            pkg: [
                # for mypy
                'py.typed',

                # empty dir, necessary for proper dynamic imports
                'mycfg_stub/repos/.gitkeep',
            ],
        },


        url='https://github.com/karlicoss/HPI',
        author='Dmitrii Gerasimov',
        author_email='karlicoss@gmail.com',
        description='A Python interface to my life',

        install_requires=INSTALL_REQUIRES,
        extras_require={
            'testing': [
                'pytest',
                'pytz',
                'pylint',
            ],
        },
    )


if __name__ == '__main__':
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument('--dependencies-only', action='store_true')
    args, _ = p.parse_known_args()
    if args.dependencies_only:
        cmd = ['pip3', 'install', '--user', *INSTALL_REQUIRES]
        scmd = ' '.join(cmd)
        import os
        xx = input(f'Run {scmd} [y/n] ')
        if xx.strip() == 'y':
            os.execvp(
                'pip3',
                cmd
            )
    else:
        main()

# TODO assert??? diff -bur my/ ~/.local/lib/python3.8/site-packages/my/
