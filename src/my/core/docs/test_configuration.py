from __future__ import annotations

from abc import abstractmethod
from collections.abc import Callable
from dataclasses import dataclass, fields
from typing import TYPE_CHECKING, Protocol, Self, assert_type

from ..common import classproperty


class user_config_good:
    require1: str = "require1"

    # NOTE: normal property here definitely wouldn't work on a class
    # also type checkers still infer type as if it's an instance property? ughh
    @classproperty
    def require2(self) -> str:
        return "require2"

    optional: str | None = "optional"


class user_config_empty:
    # whoops, forgot all required
    optional: str | None = "optional"


def test_simple() -> None:
    """
    Very basic configuration, useful when you just started working on a module.

    This doesn't work quite as expected.
    - config shadows optional from user_config_good, so default attributes don't really work.
    - need to use @classproperty (not a builtin)
    """
    class config(user_config_good):
        require1: str
        require2: str
        optional: str | None = None

    # NOTE: type asserts have to go first to avoid narrowing
    assert_type(config.require1  , str)
    assert_type(config.require2  , str)
    assert_type(config.optional  , str | None)
    assert      config.require1 == "require1"
    assert      config.require2 == "require2"
    assert      config.optional is None   # NOTE: incorrect! expecting to be "optional"


def test_combined_config() -> None:
    """
    If the previous problem was shadowing, maybe we can force different attribute resolution order by inheritance?
    This works in runtime, however big issue:
    - if we forget a required attriubute in config, we get no signal from the type checker
    """
    class Config:
        require1: str
        require2: str
        optional: str | None = None

    class config_good(user_config_good, Config):  # NOTE: (Config, user_config_good) won't work! wrong MRO
        pass

    assert_type(config_good.require1,   str)
    assert_type(config_good.require2  , str)
    assert_type(config_good.optional  , str | None)
    assert      config_good.require1 == "require1"
    assert      config_good.require2 == "require2"
    assert      config_good.optional == "optional"

    class config_empty(user_config_empty, Config):
        pass

    if TYPE_CHECKING:
        assert_type(config_empty.require1  , str)
        assert_type(config_empty.require2  , str)
    assert_type    (config_empty.optional  , str | None)
    if TYPE_CHECKING:
        # all type checks are passing -- we get no warning that some attributes are missing
        # will only fail in runtime
        assert      config_empty.require1 == "require1"  # NOTE: fails only in runtime (as expected)
        assert      config_empty.require2 == "require2"  # NOTE: fails only in runtime (as expected)
    assert          config_empty.optional == "optional"


class MakeConfigMixin:
    # TODO reuse that in existing hpi modules?
    @classmethod
    def make_config(cls) -> Self:
        base = cls.__base__
        params = {
            # NOTE: getattr helps to resolve classproperty (even possibly property?) into actual value
            f.name: getattr(base, f.name)
            for f in fields(cls)  # type: ignore[arg-type]  # wants dataclass
            if hasattr(base, f.name)
        }
        return cls(**params)


def test_dataclass_config() -> None:
    """
    Let's try using a dataclass, perhaps default attribute handing would be better.
    """
    @dataclass
    class config(user_config_good, MakeConfigMixin):
        require1: str
        require2: str
        optional: str | None = None


    assert_type(config.require1  , str)
    # assert_type(config.require2  , str)  # NOTE: complains that 'Cannot access instance-only attribute "require2" on class object'
    assert_type(config.optional  , str | None)
    assert      config.require1 == "require1"
    if not TYPE_CHECKING:
        # works in runtime though!
        assert  config.require2 == "require2"
    assert      config.optional is None   # NOTE: incorrect! expecting to be "optional"

    # if we instantiate it, seems better! this is basically the approach suggested in existing doc?
    # I think one main downside is that it requires user_config to be available on the top level
    # this makes testing things difficult. would be nice to avoid config import until the first time it's needed
    # see https://github.com/karlicoss/HPI/discussions/385#discussioncomment-10446410
    cfg = config.make_config()
    assert_type(cfg   .require1  , str)
    assert_type(cfg   .require2  , str)
    assert_type(cfg   .optional  , str | None)
    assert      cfg   .require1 == "require1"
    assert      cfg   .require2 == "require2"
    assert      cfg   .optional == "optional"


# TODO yet another different behaviour? ugh
# @dataclass
# class config(user_config_empty):
#     require1: str
#     optional: str | None = None

# # NOTE: doesn't work -- getting both type check and runtime error Cannot access instance-only attribute "require1" on class object  [misc]
# # this is somewhat expected (we do want some error if we forgot to override, albeit confusing)
# # assert      config.require1 == "require1"
# # assert_type(config.require1, str)
# assert      config.optional  == None   # NOTE: incorrect! expecting to be "optional"
# assert_type(config.optional , None)    # NOTE: incorrect! should be str | None

def test_dataclass_config_combined() -> None:
    """
    What if we do mixin + dataclass?

    More or less same thing as in test_combined_config.
    """

    @dataclass
    class Config:
        require1: str
        require2: str
        optional: str | None = None

    class config_good(user_config_good, Config, MakeConfigMixin):
        pass

    assert_type(config_good.require1  , str)
    assert_type(config_good.require2  , str)
    assert_type(config_good.optional  , str | None)
    assert      config_good.require1 == "require1"
    assert      config_good.require2 == "require2"
    assert      config_good.optional == "optional"

    cfg_good = config_good.make_config()
    assert_type(cfg_good   .require1  , str)
    assert_type(cfg_good   .require2  , str)
    assert_type(cfg_good   .optional  , str | None)
    assert      cfg_good   .require1 == "require1"
    assert      cfg_good   .require2 == "require2"
    assert      cfg_good   .optional == "optional"

    # Maybe at least it works better with empty configs?
    # Nope, basically same thing as in test_simple_base_empty_user
    class config_empty(user_config_empty, Config, MakeConfigMixin):
        pass

    if TYPE_CHECKING:
        # as expected, triggers type error (albeit confusing one)
        # "Cannot access instance-only attribute "require1" on class object"
        # hmm this is actually why CI was failing here
        # https://github.com/karlicoss/HPI/actions/runs/25573753199/job/75075717847
        # AND IT WAS RIGHT!
        # I should have probably updated the config stub to include default values...
        assert_type(config_empty.require1  , str)  # type: ignore[misc]
        assert_type(config_empty.require2  , str)  # type: ignore[misc]
    assert_type    (config_empty.optional  , str | None)
    if TYPE_CHECKING:
        assert      config_empty.require1 == "require1"  # type: ignore[misc]
        assert      config_empty.require2 == "require2"  # type: ignore[misc]
    assert          config_empty.optional == "optional"

    if TYPE_CHECKING:
        # NOTE: fails to instantiate config here in runtime, as expected.. but no indication from the type checker
        cfg_empty = config_empty.make_config()
        assert_type(cfg_empty   .require1   , str)
        assert_type(cfg_empty   .require2   , str)
        assert_type(cfg_empty   .optional   , str | None)
        assert      cfg_empty   .require1 == "require1"
        assert      cfg_empty   .require2 == "require2"
        assert      cfg_empty   .optional == "optional"

# OK, so overall dataclass based approach isn't bad, however
# - confusing errors if config attributes are missing


def test_protocol() -> None:
    class Config(Protocol):  # NOTE: Protocol can't inherit from non-protocol. so Config(user_config_good, Protocol) wouldn't work anyway
        require1: str
        require2: str
        optional: str | None = None

    class config_good(user_config_good, Config):
        pass

    assert_type(config_good .require1  , str)
    assert_type(config_good .require2  , str)
    assert_type(config_good .optional  , str | None)
    assert      config_good .require1 == "require1"
    assert      config_good .require2 == "require2"
    assert      config_good .optional == "optional"

    cfg_good = config_good()
    assert_type(cfg_good    .require1  , str)
    assert_type(cfg_good    .require2  , str)
    assert_type(cfg_good    .optional  , str | None)
    assert      cfg_good    .require1 == "require1"
    assert      cfg_good    .require2 == "require2"
    assert      cfg_good    .optional == "optional"

    class config_empty(user_config_empty, Config):
        pass

    # Hmm not ideal -- mypy doesn't complain at all about missing attributes
    if TYPE_CHECKING:
        assert_type(config_empty.require1  , str)
        assert_type(config_empty.require2  , str)
    assert_type(config_empty    .optional  , str | None)
    if TYPE_CHECKING:
        assert config_empty     .require1 == "require1"
        assert config_empty     .require2 == "require2"
    assert      config_empty    .optional == "optional"

    if TYPE_CHECKING:
        # nice! complains that
        # Cannot instantiate abstract class "config_empty" with abstract attributes "require2" and "require1"
        _cfg_empty = config_empty()  # type: ignore[abstract]


def test_properties() -> None:
    class Config:
        @property
        @abstractmethod
        def require1(self) -> str: ...

        @property
        @abstractmethod
        def require2(self) -> str: ...

        @property
        def optional(self) -> str | None:
            return None

    class config_good(user_config_good, Config):
        pass

    assert_type(config_good .require1  , str)
    assert_type(config_good .require2  , str)
    assert_type(config_good .optional  , str | None)
    assert      config_good .require1 == "require1"
    assert      config_good .require2 == "require2"
    assert      config_good .optional == "optional"

    cfg_good = config_good()
    assert_type(cfg_good    .require1  , str)
    assert_type(cfg_good    .require2  , str)
    assert_type(cfg_good    .optional  , str | None)
    assert      cfg_good    .require1 == "require1"
    assert      cfg_good    .require2 == "require2"
    assert      cfg_good    .optional == "optional"

    class config_empty(user_config_empty, Config):
        pass

    # NOTE: doesn't work! says that Expression is of type "Callable[[Config], str]", not "str"  [assert-type]
    if TYPE_CHECKING:
        assert_type(config_empty.require1  , str)  # type: ignore[assert-type] # ty: ignore[type-assertion-failure]
        assert_type(config_empty.require2  , str)  # type: ignore[assert-type] # ty: ignore[type-assertion-failure]
    assert_type(    config_empty.optional  , str | None)
    if TYPE_CHECKING:
        # also fails runtime (as expected), but in a confusing way -- returns property object, not missing attribute error
        assert      config_empty.require1 == "require1"  # type: ignore[comparison-overlap]
        assert      config_empty.require2 == "require2"  # type: ignore[comparison-overlap]
    assert          config_empty.optional == "optional"

    if TYPE_CHECKING:
        # nice! that fails with a good type error
        # Cannot instantiate abstract class "config_empty" with abstract attributes "require2" and "require1"
        # and also will fail in runtime
        _cfg_empty = config_empty()  # type: ignore[abstract]


# OK so seems like if we are on happy path or using config class directly rather than object things,
#  generally just work as expected regardless whether we use abstract class or Protocol.. hmm
#  so perhaps let's try not using classproperties..

if TYPE_CHECKING:
    # TODO move to core?
    from typing import Any
    def lazy[T](_: Callable[[Any], T]) -> T:
        ...
else:
    lazy = property


# just to give Protocol another change, we could hack @property to present differently to the type checker
class user_config_good_lazy_property:
    require1: str = "require1"

    # described here
    # https://github.com/karlicoss/HPI/discussions/385#discussioncomment-10446414
    @lazy
    def require2(self) -> str:
        return "require2"

    optional: str | None = "optional"


def test_protocol_lazy_property() -> None:
    class Config(Protocol):
        require1: str
        require2: str
        optional: str | None = None

    # ok interesting that works!
    class config_good(user_config_good_lazy_property, Config):
        pass

    assert_type(config_good .require1  , str)
    assert_type(config_good .require2  , str)
    assert_type(config_good .optional  , str | None)
    assert      config_good .require1 == "require1"
    if TYPE_CHECKING:
        # NOTE: doesn't work in runtime, just returns property object
        assert  config_good .require2 == "require2"
    assert      config_good .optional == "optional"

    cfg_good = config_good()
    assert_type(cfg_good    .require1  , str)
    assert_type(cfg_good    .require2  , str)
    assert_type(cfg_good    .optional  , str | None)
    assert      cfg_good    .require1 == "require1"
    assert      cfg_good    .require2 == "require2"
    assert      cfg_good    .optional == "optional"


class user_config_good_instance_property:
    require1: str = "require1"

    @property
    def require2(self) -> str:
        return "require2"

    optional: str | None = "optional"


def test_protocol_instance_property() -> None:
    class Config(Protocol):
        require1: str
        require2: str
        optional: str | None = None

    # Cannot override writeable attribute "require2" in base "Config" with read-only property in base "user_config_good_2"  [override]
    # this is because protocol variables are read-write by default; wheras @property is read only
    # so this is sort of a no-go
    class config_good(user_config_good_instance_property, Config):  # type: ignore[override]
        pass


def test_properties_instance_property() -> None:
    """
    This seems to be the best approach considering all factors; recommended in the documentation.
    """
    class Config:
        @property
        @abstractmethod
        def require1(self) -> str: ...

        @property
        @abstractmethod
        def require2(self) -> str: ...

        @property
        def optional(self) -> str | None:
            return None

    class config_good(user_config_good_instance_property, Config):
        pass

    # because we use a normal @property now, using config class directly doesn't work well -- fair enough
    assert_type(config_good .require1  , str)
    assert_type(config_good .require2  , str)  # type: ignore[assert-type]  # ty: ignore[type-assertion-failure]
    assert_type(config_good .optional  , str | None)
    assert      config_good .require1 == "require1"
    if TYPE_CHECKING:
        assert  config_good .require2 == "require2"  # type: ignore[comparison-overlap]
    assert      config_good .optional == "optional"

    cfg_good = config_good()
    assert_type(cfg_good    .require1  , str)
    assert_type(cfg_good    .require2  , str)
    assert_type(cfg_good    .optional  , str | None)
    assert      cfg_good    .require1 == "require1"
    assert      cfg_good    .require2 == "require2"
    assert      cfg_good    .optional == "optional"


# TODO things to think about
# - should the schema be Config? kind of more consistent naming (although not a huge deal)
#   that would make it easier to instantiate, e.g. could make a lazy attribute in module
#   like config = Lazy(make_config)
