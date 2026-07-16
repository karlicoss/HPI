# HPI docs


- [Docs](#docs)
- [Legacy (org, being migrated)](#legacy-org-being-migrated)

Render all documentation with `tox -e quarto`. For live browser preview,
run `uv run --only-group quarto quarto preview doc --profile preview`
from the repository root.

With `freeze: auto`, Quarto only detects changes to `.qmd` files. After
editing `quarto_helpers.py`, run `tox -e quarto -- --execute` or delete
`_freeze/` to re-execute the docs that import it.

# Docs

User guides:

- [Configuring modules](configuring_modules.md)
- [Querying HPI](QUERY.md)
- [Denylists](DENYLIST.md)

Architecture decisions:

- [Configuration requirements](configuration_requirements.md)

# Legacy (org, being migrated)

- [CONFIGURING](CONFIGURING.org)
- [CONTRIBUTING](CONTRIBUTING.org)
- [DESIGN](DESIGN.org)
- [DEVELOPMENT](DEVELOPMENT.org)
- [MODULES](MODULES.org)
- [MODULE_DESIGN](MODULE_DESIGN.org)
- [OVERLAYS](OVERLAYS.org)
- [SETUP](SETUP.org)
