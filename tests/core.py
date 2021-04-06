'''
NOTE: Sigh. it's nice to be able to define the tests next to the source code (so it serves as documentation).
However, if you run 'pytest --pyargs my.core', it detects 'core' package name (because there is no my/__init__.py)
(see https://docs.pytest.org/en/latest/goodpractices.html#tests-as-part-of-application-code)

This results in relative imports failing (e.g. from ..kython import...).

By using this helper file, pytest can detect the package name properly. A bit meh, but perhaps after kython is moved into the core,
we can run against the tests in my.core directly.

'''

from my.core.cfg            import *
from my.core.common         import *
from my.core.core_config    import *
from my.core.error          import *
from my.core.util           import *
from my.core.discovery_pure import *
from my.core.freezer        import *
from my.core.stats          import *
from my.core.query          import *
from my.core.query_range    import *
from my.core.serialize      import test_serialize_fallback
from my.core.sqlite         import *
from my.core.__main__       import *
