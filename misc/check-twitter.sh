#!/bin/bash
# just a hacky script to check twitter module behaviour w.r.t. merging and normalising data
# this checks against orger output for @karlicoss data

set -eu

FILE="$1"

function check() {
   x="$1"
   if [[ $(rg --count "$x" "$FILE") != "1" ]]; then
      echo "FAILED! $x"
   fi
}

# only in old twitter archive data + test mentions
check '2010-03-24 Wed 10:02.*@GDRussia подлагивает'

# check that old twitter archive data replaces &lt/&gt
check '2011-05-12 Thu 17:51.*set ><'
# this would probs be from twint or something?
check '2013-06-01 Sat 18:48.*<inputfile'


# https://twitter.com/karlicoss/status/363703394201894912
# the quoted acc was suspended and the tweet is only present in archives?
check '2013-08-03 Sat 16:50.*удивительно, как в одном человеке'
# similar
# https://twitter.com/karlicoss/status/712186968382291968
check '2016-03-22 Tue 07:59.*Очень хорошо'


# RTs are missing from twint
# https://twitter.com/karlicoss/status/925968541458759681
check '2017-11-02 Thu 06:11.*RT @dabeaz: A short esoteric Python'


# twint stopped updating at this point
# https://twitter.com/karlicoss/status/1321488603499954177
check '2020-10-28 Wed 16:26.*@jborichevskiy I feel like for me'

# https://twitter.com/karlicoss/status/808769414984331267
# archive doesn't expland links in 'text' by default, check we're doing that in HPI
# NOTE: hmm twint adds an extra whitespace here before the link?
check '2016-12-13 Tue 20:23.*TIL:.*pypi.python.org/pypi/coloredlogs'


# https://twitter.com/karlicoss/status/472151454044917761
# archive isn't expanding images by default
check '2014-05-29 Thu 23:04.*Выколол сингулярность.*pic.twitter.com/M6XRN1n7KW'


# https://twitter.com/karlicoss/status/565648186816335873
# for some reason missing from twint??
check '2015-02-11 Wed 23:06.*separation confirmed'


# mentions were missing from twint at some point, check they are still present..
# https://twitter.com/karlicoss/status/1228225797283966976
check '2020-02-14 Fri 07:53.*thomas536.*looks like a very cool blog'


# just a random timestamp check. RT then reply shortly after -- good check.
# https://twitter.com/karlicoss/status/341512959694082049
check '2013-06-03 Mon 11:13.*RT @osenin'
# https://twitter.com/karlicoss/status/341513515749736448
check '2013-06-03 Mon 11:15.*@osenin'


# def was tweeted at 00:00 MSK, so a good timezone check
# id 550396141914058752
check '2014-12-31 Wed 21:00.*2015 заебал'

# for some reason is gone, and wasn't in twidump/twint
# https://twitter.com/karlicoss/status/1393312193945513985
check '2021-05-14 Fri 21:08.*RT @SNunoPerez: Me explaining Rage.*'


# make sure there is a single occurrence (hence, correct tzs)
check 'A short esoteric Python'
# https://twitter.com/karlicoss/status/1499174823272099842
check 'It would be a really good time for countries'
# https://twitter.com/karlicoss/status/1530303537476947968
check 'so there is clearly a pattern'


# https://twitter.com/karlicoss/status/1488942357303238673
# check URL expansion for Talon
check '2022-02-02 Wed 18:28.*You are in luck!.*https://deepmind.com/blog/article/Competitive-programming-with-AlphaCode'


# https://twitter.com/karlicoss/status/349168455964033024
# check link which is only in twidump
check '2013-06-24 Mon 14:13.*RT @gorod095: Нашел недавно в букинист'

# some older statuses, useful to test that all input data is properly detected
check '2010-04-01 Thu 11:34'
check '2010-06-28 Mon 23:42'

# https://twitter.com/karlicoss/status/22916704915
# this one is weird, just disappeared for no reason between 2021-12-22 and 2022-03-15
# and the account isn't suspended etc. maybe it was temporary private or something?
check '2010-09-03 Fri 20:11.*Джобс'

# TODO check likes as well
