# HPI modules


- [Intro](#intro)
- [all.py](#allpy)
- [Configs](#configs)
  - [my.reddit](#myreddit)
  - [my.browser](#mybrowser)
  - [my.location](#mylocation)
  - [my.time.tz.via_location](#mytimetzvia_location)
  - [my.google.takeout.parser](#mygoogletakeoutparser)
  - [my.hypothesis](#myhypothesis)
  - [my.pocket](#mypocket)
  - [my.twitter.twint](#mytwittertwint)
  - [my.twitter.archive](#mytwitterarchive)
  - [my.lastfm](#mylastfm)
  - [my.polar](#mypolar)
  - [my.instapaper](#myinstapaper)
  - [my.github.gdpr](#mygithubgdpr)
  - [my.github.ghexport](#mygithubghexport)
  - [my.kobo](#mykobo)

This file is an overview of **documented** modules, which I’m
progressively expanding.

There are many more:

- [“What’s inside”](../README.org#whats-inside) for the full list of
  modules.
- run `hpi modules` to list what’s available on your system
- the [source tree](../src/my/) is always the primary source of truth

If you have some issues with the setup, see
[“Troubleshooting”](SETUP.org#troubleshooting).

# Intro

See [SETUP](SETUP.org) to find out how to set up your own config.

Some explanations:

- `MY_CONFIG` is the path where you are keeping your private
  configuration (usually `~/.config/my/`)

- [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path) is
  a standard Python object to represent paths

- [Paths](https://github.com/karlicoss/HPI/blob/master/src/my/core/common.py#L12)
  is another helper type for paths.

  It’s ‘smart’, allows you to be flexible about your config:

  - simple `str` or a `Path`

  - `/a/path/to/directory/`, so the module will consume all files from
    this directory

  - a list of files/directories (it will be flattened)

  - a
    [glob](https://docs.python.org/3/library/glob.html?highlight=glob#glob.glob)
    string, so you can be flexible about the format of your data on disk
    (e.g. if you want to keep it compressed)

  - empty string (e.g. `export_path = ''`), this will prevent the module
    from consuming any data

    This can be useful for modules that merge multiple data sources (for
    example, `my.twitter` or `my.github`)

  Typically, such variable will be passed to `get_files` to actually
  extract the list of real files to use. You can see usage examples
  [here](../src/my/core/tests/test_get_files.py).

- if the field has a default value, you can omit it from your private
  config altogether

For more thoughts on modules and their structure, see
[MODULE_DESIGN](MODULE_DESIGN.org)

# all.py

Some modules have lots of different sources for data. For example,
`my.location` (location data) has lots of possible sources – from
`my.google.takeout.parser`, using the `gpslogger` android app, or
through geolocating `my.ip` addresses. If you only plan on using one the
modules, you can just import from the individual module,
(e.g. `my.google.takeout.parser`) or you can disable the others using
the `core` config – See the [MODULE_DESIGN](MODULE_DESIGN.org#allpy)
docs for more details.

# Configs

The config snippets below are meant to be modified accordingly and
**pasted into your private configuration**, e.g
`$MY_CONFIG/my/config.py`.

You don’t have to set up all modules at once, it’s recommended to do it
gradually, to get the feel of how HPI works.

For an extensive/complex example, you can check out `@purarue`’s
[config](https://github.com/purarue/dotfiles/blob/master/.config/my/my/config/__init__.py)

## [my.reddit](../src/my/reddit)

Reddit data: saved items/comments/upvotes/etc.

``` python
class reddit:
    class rexport:
        '''
        Uses [[https://github.com/karlicoss/rexport][rexport]] output.
        '''

        # path[s]/glob to the exported JSON data
        export_path: Paths

    class pushshift:
        '''
        Uses [[https://github.com/purarue/pushshift_comment_export][pushshift]] to get access to old comments
        '''

        # path[s]/glob to the exported JSON data
        export_path: Paths
```

## [my.browser](../src/my/browser/)

Parses browser history using
[browserexport](http://github.com/purarue/browserexport)

``` python
class browser:
    class export:
        # path[s]/glob to your backed up browser history sqlite files
        export_path: Paths

    class active_browser:
        # paths to sqlite database files which you use actively
        # to read from. For example:
        # from browserexport.browsers.all import Firefox
        # export_path = Firefox.locate_database()
        export_path: Paths
```

## [my.location](../src/my/location)

Merged location history from lots of sources.

The main sources here are
[gpslogger](https://github.com/mendhak/gpslogger) .gpx (XML) files, and
google takeout (using `my.google.takeout.parser`), with a fallback on
manually defined home locations.

You might also be able to use
[my.location.via_ip](../src/my/location/via_ip.py) which uses
`my.ip.all` to provide geolocation data for an IPs (though no IPs are
provided from any of the sources here). For an example of usage, see
[here](https://github.com/purarue/HPI/tree/master/my/ip)

``` python
class location:
    home = (
         # supports ISO strings
         ('2005-12-04'                                       , (42.697842, 23.325973)), # Bulgaria, Sofia
         # supports date/datetime objects
         (date(year=1980, month=2, day=15)                   , (40.7128  , -74.0060 )), # NY
         (datetime.fromtimestamp(1600000000, tz=timezone.utc), (55.7558  , 37.6173  )), # Moscow, Russia
     )
     # note: order doesn't matter, will be sorted in the data provider

     class gpslogger:
         # path[s]/glob to the exported gpx files
          export_path: Paths

          # default accuracy for gpslogger
          accuracy: float = 50.0

      class via_ip:
          # guess ~15km accuracy for IP addresses
          accuracy: float = 15_000
```

## [my.time.tz.via_location](../src/my/time/tz/via_location.py)

Uses the `my.location` module to determine the timezone for a location.

This can be used to ‘localize’ timezones. Most modules here return
datetimes in UTC, to prevent confusion whether or not its a local
timezone, one from UTC, or one in your timezone.

Depending on the specific data provider and your level of paranoia you
might expect different behaviour.. E.g.:

- if your objects already have tz info, you might not need to call
  localize() at all
- it’s safer when either all of your objects are tz aware or all are tz
  unware, not a mixture
- you might trust your original timezone, or it might just be UTC, and
  you want to use something more reasonable

``` python
TzPolicy = Literal[
    'keep'   , # if datetime is tz aware, just preserve it
    'convert', # if datetime is tz aware, convert to provider's tz
    'throw'  , # if datetime is tz aware, throw exception
]
```

This is still a work in progress, plan is to integrate it with
`hpi query` so that you can easily convert/localize timezones for some
module/data

``` python
class time:
    class tz:
        policy = 'keep'

        class via_location:
            # less precise, but faster
            fast: bool = True

            # sort locations by date
            # in case multiple sources provide them out of order
            sort_locations: bool = True

            # if the accuracy for the location is more than 5km (this
            # isn't an accurate location, so shouldn't use it to determine
            # timezone), don't use
            require_accuracy: float = 5_000
```

<span id="mygoogletakeoutpaths"></span>

## [my.google.takeout.parser](../src/my/google/takeout/parser.py)

Parses Google Takeout using
[google_takeout_parser](https://github.com/purarue/google_takeout_parser)

See
[google_takeout_parser](https://github.com/purarue/google_takeout_parser)
for more information about how to export and organize your takeouts

If the DISABLE_TAKEOUT_CACHE environment variable is set, this won’t
cache individual exports in ~/.cache/google_takeout_parser

The directory set as takeout_path can be unpacked directories, or zip
files of the exports, which are temporarily unpacked while creating the
cachew cache

``` python
class google:
    # directory which includes unpacked/zipped takeouts
    takeout_path: Paths

    error_policy: ErrorPolicy = 'yield'

    # experimental flag to use kompress.ZipPath
    # instead of unpacking to a tmp dir via match_structure
    _use_zippath: bool = False
```

## [my.hypothesis](../src/my/hypothesis.py)

[Hypothes.is](https://hypothes.is) highlights and annotations

``` python
class hypothesis:
    '''
    Uses [[https://github.com/karlicoss/hypexport][hypexport]] outputs
    '''

    # paths[s]/glob to the exported JSON data
    export_path: Paths
```

## [my.pocket](../src/my/pocket.py)

[Pocket](https://getpocket.com) bookmarks and highlights

``` python
class pocket:
    '''
    Uses [[https://github.com/karlicoss/pockexport][pockexport]] outputs
    '''

    # paths[s]/glob to the exported JSON data
    export_path: Paths
```

## [my.twitter.twint](../src/my/twitter/twint.py)

Twitter data (tweets and favorites). Uses
[Twint](https://github.com/twintproject/twint) data export.

``` python
class twint:
    export_path: Paths  # path[s]/glob to the twint Sqlite database
```

## [my.twitter.archive](../src/my/twitter/archive.py)

Twitter data (uses [official twitter archive
export](https://help.twitter.com/en/managing-your-account/how-to-download-your-twitter-archive))

``` python
class twitter_archive:
    # path[s]/glob to the twitter archive takeout
    export_path: Paths
```

## [my.lastfm](../src/my/lastfm.py)

Last.fm scrobbles

``` python
class lastfm:
    # Uses [[https://github.com/karlicoss/lastfm-backup][lastfm-backup]] outputs
    export_path: Paths
```

## [my.polar](../src/my/polar.py)

[Polar](https://github.com/burtonator/polar-bookshelf) articles and
highlights

``` python
class polar:
    '''
    Polar config is optional, you only need it if you want to specify custom 'polar_dir'
    '''

    polar_dir: Path | str = Path('~/.polar').expanduser()  # noqa: RUF009
    defensive: bool = True  # pass False if you want it to fail faster on errors (useful for debugging)
```

## [my.instapaper](../src/my/instapaper.py)

[Instapaper](https://www.instapaper.com) bookmarks, highlights and
annotations

``` python
class instapaper:
    '''
    Uses [[https://github.com/karlicoss/instapexport][instapexport]] outputs.
    '''

    # path[s]/glob to the exported JSON data
    export_path: Paths
```

## [my.github.gdpr](../src/my/github/gdpr.py)

Github data (uses [official GDPR
export](https://github.com/settings/admin))

``` python
class github:
    gdpr_dir: Paths
```

## [my.github.ghexport](../src/my/github/ghexport.py)

Github data: events, comments, etc. (API data)

``` python
class github:
    '''
    Uses [[https://github.com/karlicoss/ghexport][ghexport]] outputs.
    '''

    export_path: Paths
    '''path[s]/glob to the exported JSON data'''
```

## [my.kobo](../src/my/kobo.py)

[Kobo](https://uk.kobobooks.com/products/kobo-aura-one) e-ink reader:
annotations and reading stats

``` python
class kobo:
    '''
    Uses [[https://github.com/karlicoss/kobuddy#as-a-backup-tool][kobuddy]] outputs.
    '''

    # path[s]/glob to the exported databases
    export_path: Paths
```
