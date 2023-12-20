from setuptools import setup, find_namespace_packages # type: ignore


def main() -> None:
    pkgs = find_namespace_packages('src')
    pkg = min(pkgs)
    setup(
        name='hpi-overlay',
        zip_safe=False,
        packages=pkgs,
        package_dir={'': 'src'},
        package_data={pkg: ['py.typed']},
    )


if __name__ == '__main__':
    main()
