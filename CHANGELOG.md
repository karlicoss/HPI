# `v0.3.20210220`

General/my.core changes:

- a3305677b24694391a247fc4cb6cc1237e57f840 **deprecate*** my.cfg, instead my.config can (and should be) used directly
- 0534c5c57dc420f9a01387b58a7098823e54277e new cli feature: **module management**

    cli: add `hpi module install` and `hpi module requires`

    relevant: https://github.com/karlicoss/HPI/issues/12, https://github.com/karlicoss/HPI/issues/79

- 97650adf3b48c653651b31c78cefe24ecae5ed4f add discovery_pure module to get modules and their dependencies via `ast` module
- f90599d7e4463e936c8d95196ff767c730207202 make module discovery rely on `ast` module
  Hopefully it will make it more robust & much faster.
- 07f901e1e5fb2bd3009561c84cc4efd311c94733 helpers for **automatic dataframes** from sequences of NamedTuple/dataclass
- 4012f9b7c2a429170df8600591ec8d1e1407b162 more generic functions to jsonify data
- 746c3da0cadcba3b179688783186d8a0bd0999c5 core.pandas: allow specifying schema; add tests
- 5313984d8fea2b6eef6726b7b346c1f4316acd01 add `tmp_config` context manager for test & adhoc patching
- df9a7f7390aee6c69f1abf1c8d1fc7659ebb957c core.pandas: add check for 'error' column + add empty one by default
- e81dddddf083ffd81aa7e2b715bd34f59949479c properly resolve class properties in make_config + add test

Modules:
- some initial work on filling **InfluxDB** with HPI data

- pinboard
  - 42399f6250d9901d93dcedcfe05f7857babcf834: **breaking backwards compatibility**, use pinbexport module directly

    Use 'hpi module install my.pinboard' to install it

    relevant: https://github.com/karlicoss/HPI/issues/79

- stackexchange
  - 63c825ab81bb561e912655e423c6b332fb6fd1b4 use GDPR data for votes
  - ddea816a49f5da79fd6332e7f6b879b1955838af use proper pip package, add stat

- bluemaestro
  - 6d9bc2964b24cfe6187945f4634940673dfe9c27 populate grafana
  - 1899b006de349140303110ca98a21d918d9eb049 investigation of data quality + more sanity checks
  - d77ab92d8634d0863d2b966cb448bbfcc8a8d565 get rid of unnecessary file, move to top level

- runnerup
  - 6b451336ed5df2b893c9e6387175edba50b0719b Initial parser for RunnerUp data which I'm now using instead of Endomondo

Misc:
- f102101b3917e8a38511faa5e4fd9dd33d284d7e core/windows: fix get_files and its tests
- 56d5587c209dcbd27c7802d60c0bc8e8e2391672 CI: clean up tox config a bit, get rid of custom lint script
- d562f00dca720fd4f6736377a41168e9a796c122

    tests: run all tests, but exclude tests specific to my computer from CI
    controllable via `HPI_TESTS_KARLICOSS=true`

- improved mypy coverage


# before `v0.2.20201125`

I used to keep it in [Github releases](https://github.com/karlicoss/HPI/releases).
However I realized it's means promoting a silo, so now it's reflected in this file (and only copied to github releases page).
