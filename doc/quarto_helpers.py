import tomllib
from pathlib import Path

import jedi

REPO = Path(__file__).parent.parent
SRC = REPO / "src"

with (REPO / "pyproject.toml").open("rb") as fo:
    pyproject = tomllib.load(fo)
GITHUB = pyproject["project"]["urls"]["Homepage"]
assert isinstance(GITHUB, str), GITHUB
assert GITHUB.startswith("https://github.com/"), GITHUB

project = jedi.Project(SRC)


def github_link(name: str) -> str:
    completions = list(project.complete_search(name, all_scopes=True))
    assert len(completions) == 1, f"Expected one completion for {name}, got {completions}"
    [c] = completions
    [c] = c.goto()
    rpath = Path(c.module_path).relative_to(SRC)
    return f"{GITHUB}/blob/master/src/{rpath}#L{c.line}"
