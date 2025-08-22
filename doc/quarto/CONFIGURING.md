# HPI configuration design


- [Configuration requirements](#configuration-requirements)
  - [Very **flexible**](#req-flexible)
  - [**Backwards compatible**](#req-backwards-compatible)
  - [As **easy to write** as possible](#req-easy-to-write)
  - [As **easy to use and extend** as possible](#req-easy-to-use)
  - [**Lintable** (statically checked)](#req-lintable)
  - [**Easy to document** (or with minimal
    effort)](#req-easy-to-document)
- [Solution?](#solution)
  - [Initial approach](#initial-approach)
  - [typing.Protocol](#typingprotocol)
  - [NamedTuple](#namedtuple)
  - [dataclass](#dataclass)
  - [Combined approach](#combined-approach)
  - [Other rejected alternatives](#other-rejected-alternatives)
- [Conclusion](#conclusion)

<!-- to render: quarto render CONFIGURING.qmd -->

<!-- TODO FFS can't prevent TOC from collapsing???  https://github.com/quarto-dev/quarto-cli/discussions/3107 -->

This doc describes the technical decisions behind HPI configuration
system. It’s more of a ‘design doc’ rather than usage guide. If you just
want to know how to set up HPI or configure it, see
[SETUP](../SETUP.org).

I feel like it’s good to keep the rationales in the documentation, but
happy to [discuss](https://github.com/karlicoss/HPI/issues/46) it here.

## Configuration requirements

Before discussing the abstract matters, let’s consider a specific
situation. Say, we want to let the user configure
[bluemaestro](https://github.com/karlicoss/HPI/blob/master/src/my/bluemaestro.py#L1)
module. At the moment, it uses the following config attributes:

- `export_path`

  Path to the data, this is obviously a **required** attribute

- `cache_path`

  Cache is extremely useful to speed up some queries. But it’s
  **optional**, everything should work without it.

I’ll refer to this config as **example** further in the doc, and give
examples to each point. Note that they are only illustrating the
specific requirement, potentially ignoring the other ones.

Now, the requirements as I see it:

<!-- TODO remove numbers here? -->

### Very **flexible**

**Motivation:** we need to make sure it’s very easy to
combine/filter/extend data without having to turn the module code inside
out. This means using a powerful language for config, and realistically,
a Turing complete.

That means that you should be able to use powerful syntax, potentially
running arbitrary code if this is something you need (for whatever mad
reason). It should be possible to override config attributes *in
runtime*, if necessary, without rewriting files on the filesystem.

**Example:** we’ve got Python already, so it makes a lot of sense to use
it!

``` python
class bluemaestro:
    export_path = '/path/to/bluemaestro/data'
    cache_path  = '/tmp/bluemaestro.cache'
```

**Downsides:**

- keeping it overly flexible and powerful means it’s potentially less
  accessible to people less familiar with programming

  But see the further point about keeping it simple. I claim that simple
  programs look as easy as simple JSON.

- Python is ‘less safe’ than a plain JSON/YAML config

  But at the moment the whole thing is running potentially untrusted
  Python code anyway. It’s not a tool you’re going to install it across
  your organization, run under root privileges, and let the employers
  tweak it.

  Ultimately, you set it up for yourself, and the config has exactly the
  same permissions as the code you’re installing. Thinking that plain
  config would give you more security is deceptive, and it’s a false
  sense of security (at this stage of the project).

<!--
TODO I don't mind having JSON/TOML/whatever, but only as an additional interface
-->

I also write more about all this
[here](https://beepb00p.xyz/configs-suck.html).

### **Backwards compatible**

**Motivation:** the whole system is pretty chaotic, it’s hard to control
the versioning of different modules and their mutual compatibility. It’s
important to allow changing attribute names and adding new
functionality, while making sure the module works against an older
version of the config. Ideally warn the user that they’d better migrate
to a newer version if the fallbacks are triggered. Potentially: use
individual versions for modules? Although it makes things a bit
complicated.

**Example:** say the module is using a new config attribute, `timezone`.
We would need to adapt the module to support the old configs without
timezone. For example, in `bluemaestro.py` (pseudo code):

``` python
user_config = load_user_config()
if not hasattr(user_config, 'timezone'):
    warnings.warn("Please specify 'timezone' in the config! Falling back to the system timezone.")
    user_config.timezone = get_system_timezone()
```

This is possible to achieve with pretty much any config format, just
important to keep in mind.

**Downsides:** hopefully no one argues backwards compatibility is
important.

### As **easy to write** as possible

**Motivation:** config should be as lean and non-verbose as possible, so
you could quickly start using a module or hack something together with
minimum cognitive overhead.

No extra imports, no extra inheritance, annotations, etc. Loose
coupling.

**Example:** the user *only* has to specify `export_path` to make the
module function and that’s it. For example:

``` json
{
     'export_path': '/path/to/bluemaestro/'
}
```

It’s possible to achieve with any configuration format (aided by some
helpers to fill in optional attributes etc), so it’s more of a guiding
principle.

**Downsides:**

- no (mandatory) annotations means more potential to break, but I’d
  rather leave this decision to the users

### As **easy to use and extend** as possible

**Motivation:** enable the users to add new config attributes and
*immediately* use them without any hassle and boilerplate. It’s easy to
achieve on it’s own, but harder to achieve simultaneously with
@configuration-should-be-backwards-compatible .

**Example:** if you keep the config as Python, simply importing the
config in the module satisfies this property:

``` python
from my.config import bluemaestro as user_config
```

If the config is in JSON or something, it’s possible to load it
dynamically too without the boilerplate.

**Downsides:** none, hopefully no one is against extensibility

### **Lintable** (statically checked)

**Motivation:** make sure it’s easy to track down configuration errors.
At least runtime checks for required attributes, their types, warnings,
that sort of thing. But a biggie for me is using *mypy* to statically
typecheck the modules. To some extent it gets in the way of [backwards
compatibility](#req-backwards-compatible) and [ease of
use](#req-easy-to-use).

**Example:** using `NamedTuple/dataclass` allows to verify the config
with no extra boilerplate on the user side.

``` python
class bluemaestro(NamedTuple):
     export_path: str
     cache_path : str | None = None

raw_config = json.load('configs/bluemaestro.json')
config = bluemaestro(**raw_config)
```

This will fail if required `export_path` is missing, and fill optional
`cache_path` with None. In addition, it’s `mypy` friendly when you are
using the typed config.

**Downsides:** none, especially if static checks are opt in.

### **Easy to document** (or with minimal effort)

**General:** ideally, it should be autogenerated, be self-descriptive
and have some sort of schema, to make sure the documentation (which no
one likes to write) doesn’t diverge.

**Example:** python type annotations seem like the way to go. See [the
example above](#req-lintable), it’s pretty clear from the code what
needs to be in the config.

**Downsides:** none, self-documented code is good.

## Solution?

Now I’ll consider potential solutions to the configuration, taking the
different requirements into account.

Like I already mentioned, plain configs (JSON/YAML/TOML) are very rigid
and go against [flexibility requirement](#req-flexible), which in my
opinion think makes them no-go.

So: my suggestion is to write the **configs as Python code**. It’s hard
to satisfy all requirements **at the same time**, but I want to argue
that it’s possible to satisfy most of them, depending on the maturity of
the module which we’re configuring.

### Initial approach

Let’s say you want to write a new module. You start with a

``` python
class bluemaestro:
    export_path = '/path/to/bluemaestro/data'
    cache_path  = '/tmp/bluemaestro.cache'
```

And to use it:

``` python
from my.config import bluemaestro as user_config
```

Let’s go through requirements:

- [flexibility](#req-flexible): **yes**, simply importing Python code is
  as flexible as you can get

  In addition, in runtime, you can simply assign a new config if you
  need some dynamic hacking:

  ``` python
  class new_config:
      export_path = '/some/hacky/dynamic/path'
  my.config = new_config
  ```

  After that, `my.bluemaestro` would run against your new config.

- [backwards compatibility](#req-backwards-compatible): **no**, but
  backwards compatibility is not necessary in the first version of the
  module

- [easy to write](#req-easy-to-write): **yes**, whatever is in the
  config can immediately be used by the code

- [ease of use](#req-easy-to-use): **mostly**, optional fields require
  extra code though

- [static checks](#req-lintable): **mostly**, imports are transparent to
  `mypy`, although runtime type checks would be nice too

- [documentation](#req-easy-to-document): **no**, you have to guess the
  config schema from the usage.

This approach is extremely simple, and already **good enough for initial
prototyping** or **private modules**.

The main downside so far is the lack of documentation, which I’ll try to
solve next. I see mypy annotations as the only sane way to support it,
because we also get linting for free.

So we could use:

### [typing.Protocol](https://mypy.readthedocs.io/en/stable/protocols.html#simple-user-defined-protocols)

I experimented with `Protocol`
[here](https://github.com/karlicoss/HPI/pull/45/commits/90b9d1d9c15abe3944913add5eaa5785cc3bffbc).

It’s very flexible, and doesn’t impose any runtime modifications, which
makes it good for [extensibility](#req-easy-to-use).

**Downsides:**

- it doesn’t support optional attributes (optional as in non-required,
  not as `typing.Optional`), so it goes against [ease of writing new
  config](#req-easy-to-write).

<!--
TODO: check out [@runtime_checkable](https://mypy.readthedocs.io/en/stable/protocols.html#using-isinstance-with-protocols)?
-->

### NamedTuple

[Here](https://github.com/karlicoss/HPI/pull/45/commits/c877104b90c9d168eaec96e0e770e59048ce4465)
I experimented with using `NamedTuple`.

Similarly to `Protocol`, it’s self-descriptive, and in addition allows
for non-required fields.

**Downsides:**

- it goes against [extensibility](#req-easy-to-use), because
  `NamedTuple` (being a `tuple` in runtime) can only contain the
  attributes declared in the schema.

### dataclass

Similar to `NamedTuple`, but it’s possible to add extra attributes
`dataclass` with `setattr` to support [extensibility](#req-easy-to-use).

**Downsides:**

- we partially lost [linting](#req-lintable), because dynamic attributes
  are not transparent to mypy.

### Combined approach

My conclusion was using a **combined approach**:

- Use `@dataclass` base for documentation and default attributes,
  achieving ease of [documentation](#req-easy-to-document) and [writing
  a new config](#req-easy-to-write).
- Inherit the original config class to bring in the extra attributes,
  achieving [extensibility](#req-easy-to-use).

Inheritance is a standard mechanism, which doesn’t require any extra
frameworks and plays well with other Python concepts. As a specific
example:

``` python
from my.config import bluemaestro as user_config

@dataclass
class bluemaestro(user_config):
    '''
    The header of this file contributes towards the documentation
    '''
    export_path: str
    cache_path : Optional[str] = None

    @classmethod
    def make_config(cls) -> 'bluemaestro':
        params = {
            k: v
            for k, v in vars(cls.__base__).items()
            if k in {f.name for f in dataclasses.fields(cls)}
        }
        return cls(**params)

config = bluemaestro.make_config()
```

I claim this solves pretty much everything:

- **flexibility**: yes, the config attributes are preserved and can be
  anything that’s allowed in Python
- **backwards compatibility**: collaterally, we also solved it, because
  we can adapt for renames and other legacy config adaptations in
  `make_config`
- **ease of writing config**: supports default attributes, at no extra
  cost
- **ease of extending**: the user config’s attributes are available
  through the base class
- **linting**: everything is mostly transparent to mypy. There are no
  runtime type checks yet, but I think possible to integrate with
  `@dataclass`
- **documentation**: the dataclass header is easily readable, and it’s
  possible to generate the docs automatically

#### Downsides

- inheriting from `user_config` means an early import of `my.config`

  Generally it’s better to keep everything as lazy as possible and defer
  loading to the first time the config is used. This might be annoying
  at times, e.g. if you have a top-level import of you module, but no
  config.

  But considering that in 99% of cases config is going to be on the disk
  and it’s
  [possible](https://github.com/karlicoss/HPI/blob/1e6e0bd381d20437343473878c7f63b1f9d6362b/tests/demo.py#L22-L25)
  to do something dynamic like `del sys.modules['my.bluemastro']` to
  reload the config, I think it’s a minor issue.

- `make_config` allows for some mypy false negatives in the user config

  E.g. if you forgot `export_path` attribute, mypy would miss it. But
  you’d have a runtime failure, and the downstream code using config is
  still correctly type checked.

  Perhaps it will be better when [this mypy
  issue](https://github.com/python/mypy/issues/5374) is fixed.

- the `make_config` bit is a little scary and manual

  However, it’s extracted in a generic helper, and [ends up pretty
  simple](https://github.com/karlicoss/HPI/blob/d6f071e3b12ba1cd5a86ad80e3821bec004e6a6d/my/twitter/archive.py#L17)

<!--
  # In addition, it's not even necessary if you don't have optional attributes, you can simply use the class variables (i.e. ~bluemaestro.export_path~)
  # upd. ugh, you can't, it doesn't handle default attributes overriding correctly (see tests/demo.py)
  # eh. basically all I need is class level dataclass??
-->

- inheriting from `user_config` requires it to be a `class` rather than
  an `object`

  A practical downside is you can’t use something like
  `SimpleNamespace`. But considering you can easily define an ad-hoc
  `class` anywhere (arguably this is easier than an object with custom
  attributes), this is fine?

### Other rejected alternatives

#### file-config

Potentially
[file-config](https://github.com/karlicoss/HPI/issues/12#issuecomment-610038961)

However, it’s using plain files and doesn’t satisfy
[flexibility](#req-flexible) requirement.

Also not sure about [static checks](#req-lintable). `file-config` allows
using typing annotations, but I’m not convinced they would be correctly
typed with mypy, I think you need a plugin for that.

In addition, as of July 2025, the repo is archived.

## Conclusion

My conclusion is that I’m going with this approach for now. Note that at
no stage in required any changes to the user configs, so if I missed
something, it would be reversible.
<!-- TODO what did I mean here?? ^^ -->

<!--
* Side modules :noexport:
&#10;Some of TODO rexport?
&#10;To some extent, this is an experiment. I'm not sure how much value is in .
&#10;One thing are TODO software? libraries that have fairly well defined APIs and you can reasonably version them.
&#10;Another thing is the modules for accessing data, where you'd hopefully have everything backwards compatible.
Maybe in the future
&#10;I'm just not sure, happy to hear people's opinions on this.
-->
