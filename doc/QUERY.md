`hpi query` is a command line tool for querying the output of any `hpi` function.

```
Usage: hpi query [OPTIONS] FUNCTION_NAME...

  This allows you to query the results from one or more functions in HPI

  By default this runs with '-o json', converting the results to JSON and
  printing them to STDOUT

  You can specify '-o pprint' to just print the objects using their repr, or
  '-o repl' to drop into a ipython shell with access to the results

  While filtering using --order-key datetime, the --after, --before and
  --within flags parse the input to their datetime and timedelta equivalents.
  datetimes can be epoch time, the string 'now', or an date formatted in the
  ISO format. timedelta (durations) are parsed from a similar format to the
  GNU 'sleep' command, e.g. 1w2d8h5m20s -> 1 week, 2 days, 8 hours, 5 minutes,
  20 seconds

  As an example, to query reddit comments I've made in the last month

  hpi query --order-type datetime --before now --within 4w my.reddit.all.comments
  or...
  hpi query --recent 4w my.reddit.all.comments

  Can also query within a range. To filter comments between 2016 and 2018:
  hpi query --order-type datetime --after '2016-01-01' --before '2019-01-01' my.reddit.all.comments

Options:
  -o, --output [json|pprint|repl|gpx]
                                  what to do with the result [default: json]
  -s, --stream                    stream objects from the data source instead
                                  of printing a list at the end
  -k, --order-key TEXT            order by an object attribute or dict key on
                                  the individual objects returned by the HPI
                                  function
  -t, --order-type [datetime|date|int|float]
                                  order by searching for some type on the
                                  iterable
  -a, --after TEXT                while ordering, filter items for the key or
                                  type larger than or equal to this
  -b, --before TEXT               while ordering, filter items for the key or
                                  type smaller than this
  -w, --within TEXT               a range 'after' or 'before' to filter items
                                  by. see above for further explanation
  -r, --recent TEXT               a shorthand for '--order-type datetime
                                  --reverse --before now --within'. e.g.
                                  --recent 5d
  --reverse / --no-reverse        reverse the results returned from the
                                  functions
  -l, --limit INTEGER             limit the number of items returned from the
                                  (functions)
  --drop-unsorted                 if the order of an item can't be determined
                                  while ordering, drop those items from the
                                  results
  --wrap-unsorted                 if the order of an item can't be determined
                                  while ordering, wrap them into an
                                  'Unsortable' object
  --warn-exceptions               if any errors are returned, print them as
                                  errors on STDERR
  --raise-exceptions              if any errors are returned (as objects, not
                                  raised) from the functions, raise them
  --drop-exceptions               ignore any errors returned as objects from
                                  the functions
  --help                          Show this message and exit.
```

This works with any function which returns an iterable, for example `my.coding.commits`, which searches for `git commit`s on your computer:

```bash
hpi query my.coding.commits
```

When run with a module, this does some analysis of the functions in that module and tries to find ones that look like data sources. If it can't figure out which, it prompts you like:

```
Which function should be used from 'my.coding.commits'?

	1. commits
	2. repos
```

You select the one you want by clicking `1` or `2` on your keyboard. Otherwise, you can provide a fully qualified path, like:

```
hpi query my.coding.commits.repos
```

The corresponding `repos` function this queries is defined in [`my/coding/commits.py`](../src/my/coding/commits.py)

### Ordering/Filtering/Streaming

By default, this just returns the items in the order they were returned by the function. This allows you to filter by specifying a `--order-key`, or `--order-type`. For example, to get the 10 most recent commits. `--order-type datetime` will try to automatically figure out which attribute to use. If it chooses the wrong one (since `Commit`s have both a `committed_dt` and `authored_dt`), you could tell it which to use. For example, to scan my computer and find the most recent commit I made:

```
hpi query my.coding.commits.commits --order-key committed_dt --limit 1 --reverse --output pprint --stream
Commit(committed_dt=datetime.datetime(2023, 4, 14, 23, 9, 1, tzinfo=datetime.timezone(datetime.timedelta(days=-1, seconds=61200))),
       authored_dt=datetime.datetime(2023, 4, 14, 23, 4, 1, tzinfo=datetime.timezone(datetime.timedelta(days=-1, seconds=61200))),
       message='sources.smscalls: propagate errors if there are breaking '
               'schema changes',
       repo='/home/username/Repos/promnesia-fork',
       sha='22a434fca9a28df9b0915ccf16368df129d2c9ce',
       ref='refs/heads/smscalls-handle-result')
```

To instead limit in some range, you can use `--before` and `--within` to filter by a range. For example, to get all the commits I committed in the last day:

```
hpi query my.coding.commits.commits --order-type datetime --before now --within 1d
```

That prints a a list of `Commit` as JSON objects. You could also use `--output pprint` to pretty-print the objects or `--output repl` drop into a REPL.

To process the JSON, you can pipe it to [`jq`](https://github.com/stedolan/jq). I often use `jq length` to get the count of some output:

```
hpi query my.coding.commits.commits --order-type datetime --before now --within 1d | jq length
6
```

Because grabbing data `--before now` is such a common use case, the `--recent` flag is a shorthand for `--order-type datetime --reverse --before now --within`. The same as above, to get the commits from the last day:

```
hpi query my.coding.commits.commits --recent 1d | jq length
6
```

To select a range of commits, you can use `--after` and `--before`, passing ISO or epoch timestamps. Those can be full `datetimes` (`2021-01-01T00:05:30`) or just dates (`2021-01-01`). For example, to get all the commits I made on January 1st, 2021:

```
hpi query my.coding.commits.commits --order-type datetime --after 2021-01-01 --before 2021-01-02 | jq length
1
```

If you have [`dateparser`](https://github.com/scrapinghub/dateparser#how-to-use) installed, this supports dozens more natural language formats:

```
hpi query my.coding.commits.commits --order-type datetime --after 'last week' --before 'day before yesterday' | jq length
28
```

If you're having issues ordering because there are exceptions in your results not all data is sortable (may have `None` for some attributes), you can use `--drop-unsorted` to drop those items from the results, or `--drop-exceptions` to remove the exceptions

You can also stream the results, which is useful for functions that take a while to process or have a lot of data. For example, if you wanted to pick a sha hash from a particular repo, you could combine `jq` to `select` and pick that attribute from the JSON:

```
hpi query my.coding.commits.commits --recent 30d --stream | jq 'select(.repo | contains("HPI"))' | jq '.sha' -r
4afa899c8b365b3c10e468f6279c02e316d3b650
40de162fab741df594b4d9651348ee46ee021e9b
e1cb229913482074dc5523e57ef0acf6e9ec2bb2
87c13defd131e39292b93dcea661d3191222dace
02c738594f2cae36ca4fab43cf9533fe6aa89396
0b3a2a6ef3a9e4992771aaea0252fb28217b814a
84817ce72d208038b66f634d4ceb6e3a4c7ec5e9
47992b8e046d27fc5141839179f06f925c159510
425615614bd508e28ccceb56f43c692240e429ab
eed8f949460d768fb1f1c4801e9abab58a5f9021
d26ad7d9ce6a4718f96346b994c3c1cd0d74380c
aec517e53c6ac022f2b4cc91261daab5651cebf0
44b75a88fdfc7af132f61905232877031ce32fcb
b0ff6f29dd2846e97f8aa85a2ca73736b03254a8
```

`jq`s `select` function acts on a stream of JSON objects, not a list, so it filters the output of `hpi query` the objects are generated (the goal here is to conserve memory as items which aren't needed are filtered). The alternative would be to print the entire JSON list at the end, like:

`hpi query my.coding.commits.commits --recent 30d | jq '.[] | select(.repo | contains("Repos/HPI"))' | jq '.sha' -r`, using `jq '.[]'` to convert the JSON list into a stream of JSON objects.

## Usage on non-HPI code

The command can accept any qualified function name, so this could for example be used to check the output of [`promnesia`](https://github.com/karlicoss/promnesia) sources:

```
hpi query promnesia.sources.smscalls | jq length
371
```

This can be used on any function that produces an `Iterator`/`Generator` like output, as long as it can be called with no arguments.

## GPX

The `hpi query` command can also be used with the `--output gpx` flag to generate gpx files from a list of locations, like the ones defined in the `my.location` package. This could be used to extract some date range and create a `gpx` file which can then be visualized by a GUI application.

This prints the contents for the `gpx` file to STDOUT, and prints warnings for any objects it could not convert to locations to STDERR, so pipe STDOUT to a output file, like `>out.gpx`

```
hpi query my.location.all --after '2021-07-01T00:00:00' --before '2021-07-05T00:00:00' --order-type datetime --output gpx >out.gpx
```

If you want to ignore any errors, you can use `--drop-exceptions`.

To preview, you can use something like [`qgis`](https://qgis.org/en/site/) or for something easier more lightweight, [`gpxsee`](https://github.com/tumic0/GPXSee):

`gpxsee out.gpx`:

<img src="https://user-images.githubusercontent.com/7804791/232249184-7e203ee6-a3ec-4053-800c-751d2c28e690.png" width=500 alt="chicago trip" />

(Sidenote: this is [`@purarue`](https://github.com/purarue/)s locations, on a trip to Chicago)

## Python reference

The `hpi query` command is a CLI wrapper around the code in [`query.py`](../src/my/core/query.py) and [`query_range.py`](../src/my/core/query_range.py). The `select` function is the core of this, and `select_range` lets you specify dates, timedelta, start-end ranges, and other CLI-specific code.

`my.core.query.select`:

```
    A function to query, order, sort and filter items from one or more sources
    This supports iterables and lists of mixed types (including handling errors),
    by allowing you to provide custom predicates (functions) which can sort
    by a function, an attribute, dict key, or by the attributes values.

    Since this supports mixed types, there's always a possibility
    of KeyErrors or AttributeErrors while trying to find some value to order by,
    so this provides multiple mechanisms to deal with that

    'where' lets you filter items before ordering, to remove possible errors
    or filter the iterator by some condition

    There are multiple ways to instruct select on how to order items. The most
    flexible is to provide an 'order_by' function, which takes an item in the
    iterator, does any custom checks you may want and then returns the value to sort by

    'order_key' is best used on items which have a similar structure, or have
    the same attribute name for every item in the iterator. If you have a
    iterator of objects whose datetime is accessed by the 'timestamp' attribute,
    supplying order_key='timestamp' would sort by that (dictionary or attribute) key

    'order_value' is the most confusing, but often the most useful. Instead of
    testing against the keys of an item, this allows you to write a predicate
    (function) to test against its values (dictionary, NamedTuple, dataclass, object).
    If you had an iterator of mixed types and wanted to sort by the datetime,
    but the attribute to access the datetime is different on each type, you can
    provide `order_value=lambda v: isinstance(v, datetime)`, and this will
    try to find that value for each type in the iterator, to sort it by
    the value which is received when the predicate is true

    'order_value' is often used in the 'hpi query' interface, because of its brevity.
    Just given the input function, this can typically sort it by timestamp with
    no human intervention. It can sort of be thought as an educated guess,
    but it can always be improved by providing a more complete guess function

    Note that 'order_value' is also the most computationally expensive, as it has
    to copy the iterator in memory (using itertools.tee) to determine how to order it
    in memory

    The 'drop_exceptions', 'raise_exceptions', 'warn_exceptions' let you ignore or raise
    when the src contains exceptions. The 'warn_func' lets you provide a custom function
    to call when an exception is encountered instead of using the 'warnings' module

    src:            an iterable of mixed types, or a function to be called,
                    as the input to this function

    where:          a predicate which filters the results before sorting

    order_by:       a function which when given an item in the src,
                    returns the value to sort by. Similar to the 'key' value
                    typically passed directly to 'sorted'

    order_key:      a string which represents a dict key or attribute name
                    to use as they key to sort by

    order_value:    predicate which determines which attribute on an ADT-like item to sort by,
                    when given its value. lambda o: isinstance(o, datetime) is commonly passed to sort
                    by datetime, without knowing the attributes or interface for the items in the src

    default:        while ordering, if the order for an object cannot be determined,
                    use this as the default value

    reverse:        reverse the order of the resulting iterable

    limit:          limit the results to this many items

    drop_unsorted:  before ordering, drop any items from the iterable for which a
                    order could not be determined. False by default

    wrap_unsorted:  before ordering, wrap any items into an 'Unsortable' object. Place
                    them at the front of the list. True by default

    drop_exceptions: ignore any exceptions from the src

    raise_exceptions: raise exceptions when received from the input src
```

`my.core.query_range.select_range`:

```
    A specialized select function which offers generating functions
    to filter/query ranges from an iterable

    order_key and order_value are used in the same way they are in select

    If you specify order_by_value_type, it tries to search for an attribute
    on each object/type which has that type, ordering the iterable by that value

    unparsed_range is a tuple of length 3, specifying 'after', 'before', 'duration',
    i.e. some start point to allow the computed value we're ordering by, some
    end point and a duration (can use the RangeTuple NamedTuple to construct one)

    (this is typically parsed/created in my.core.__main__, from CLI flags

    If you specify a range, drop_unsorted is forced to be True
```

Those can be imported and accept any sort of iterator, `hpi query` just defaults to the output of functions here. As an example, see [`listens`](https://github.com/purarue/HPI-personal/blob/master/scripts/listens) which just passes an generator (iterator) as the first argument to `query_range`
