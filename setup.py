#!/usr/bin/env python3
# see https://github.com/karlicoss/pymplate for up-to-date reference

from setuptools import setup, find_namespace_packages # type: ignore

INSTALL_REQUIRES = [
    'pytz',           # even though it's not needed by the core, it's so common anyway...
    'appdirs',        # very common, and makes it portable
    'more-itertools', # it's just too useful and very common anyway
]


def main():
    pkg = 'my'
    subpackages = find_namespace_packages('.', include=('my.*',))
    setup(
        name='HPI', # NOTE: 'my' is taken for PyPi already, and makes discovering the project impossible. so we're using HPI
        use_scm_version={
            # TODO eh? not sure if I should just rely on proper tag naming and use use_scm_version=True
            # 'version_scheme': 'python-simplified-semver',
            'local_scheme': 'dirty-tag',
        },
        setup_requires=['setuptools_scm'],

        zip_safe=False,

        # eh. find_packages doesn't find anything
        # find_namespace_packages can't find single file packages (like my/common.py)
        packages=[pkg, *subpackages],
        package_data={
            pkg: [
                # for mypy
                'py.typed',
            ],
            # todo not sure if need py.typed for all subpackages??
            'my.config': [
                'repos/.gitkeep',
                # TODO meh, get rid of this. If I remove, hypothesis tests (messing with config) might break though
                # not sure why it's not reproducing locally underr tox
            ],
        },


        url='https://github.com/karlicoss/HPI',
        author='Dmitrii Gerasimov',
        author_email='karlicoss@gmail.com',
        description='A Python interface to my life',

        python_requires='>=3.6',
        install_requires=INSTALL_REQUIRES,
        extras_require={
            'testing': [
                'pytest',
                'pylint',
                'mypy',
                'lxml', # for mypy coverage

                # used in some tests
                'pandas',
            ],
            'optional': [
                # TODO document these?
                'logzero',
                'cachew',
                'mypy', # used for config checks
            ],
            ':python_version<"3.7"': [
                # used for some modules... hopefully reasonable to have it as a default
                'dataclasses',
            ],
        },
        entry_points={'console_scripts': ['hpi=my.core.__main__:main']},
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
