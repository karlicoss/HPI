class Modes:
    HELLO = 'hello'


def parser():
    from argparse import ArgumentParser
    p = ArgumentParser('Human Programming Interface', epilog='''
Tool for HPI.

Work in progress, will be used for config management, troubleshooting & introspection
''')
    sp = p.add_subparsers(dest='mode')
    sp.add_parser(Modes.HELLO, help='TODO just a stub, remove later')
    return p


def main():
    p = parser()
    args = p.parse_args()
    mode = args.mode
    if mode == Modes.HELLO:
        print('hi')
    else:
        import sys
        p.print_usage()
        sys.exit(1)


if __name__ == '__main__':
    main()
