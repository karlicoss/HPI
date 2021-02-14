from subprocess import check_call

def test_lists_modules() -> None:
    check_call(['hpi', 'modules'])
