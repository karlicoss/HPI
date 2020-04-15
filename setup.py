#!/usr/bin/env python3
from setuptools import setup, find_packages # type: ignore

INSTALL_REQUIRES = [
    'appdirs'
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
    setup(
        name='my',
        version='0.0.20200412',
        description='A Python interface to my life',
        url='https://github.com/karlicoss/HPI',
        author='Dmitrii Gerasimov',
        author_email='karlicoss@gmail.com',

        classifiers=[
            'Programming Language :: Python :: 3 :: Only',
            'Development Status :: 4 - Beta',
            'Environment :: Console',
            'Intended Audience :: End Users/Desktop',
            'Topic :: Scientific/Engineering :: Information Analysis',
        ],
        keywords=["pkm", "pim", "quantified-self"],

        # TODO eh, perhaps should use 'src'...
        # package_dir={'': ''},

        # eh. find_packages doesn't find anything
        # find_namespace_packages can't find isngle file namspace packages (like my/common.py)
        packages=['my', *subpackages()],
        package_data={
            'my': [
                # for mypy
                'py.typed',

                # empty dir, necessary for proper dynamic imports
                'mycfg_stub/repos/.gitkeep',
            ],
        },

        python_requires='>=3.5', # depends on the modules though..
        extras_require={
            'testing': [
                'pytest',
                'pytz',
                'pylint',
            ],
        },
        install_requires=INSTALL_REQUIRES,
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
