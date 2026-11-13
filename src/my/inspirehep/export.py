"""
[[https://inspirehep.net][InspireHEP]] data about one author: profile, employment and education, papers, collaborations, seminars, students
"""

from __future__ import annotations

import json
import re
from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime
from functools import lru_cache
from pathlib import Path
from typing import Any

from my.core import Paths, Res, Stats, get_files, make_config, make_logger, stat

from .common import (
    Advisor,
    CitationSummary,
    Collaboration,
    Experiment,
    Membership,
    Paper,
    Position,
    Profile,
    Seminar,
    Student,
)

import my.config  # isort: skip


@dataclass
class inspirehep(my.config.inspirehep):
    '''
    Uses JSON dumps of the InspireHEP API, such as those made by [[https://github.com/brettviren/orgface][orgface]] (=orgface slurp inspirehep=)
    '''

    # paths[s]/glob to the dumps, e.g. a directory of inspirehep-YYYY-MM-DD.json
    export_path: Paths


config = make_config(inspirehep)

logger = make_logger(__name__)

# the dump format this reads
FORMAT = 1


def inputs() -> Sequence[Path]:
    return tuple(p for p in get_files(config.export_path) if p.suffix == '.json')


# -- reading the dumps


@dataclass(frozen=True)
class Dump:
    """What the newest dumps hold, part by part."""

    author: dict | None
    literature: list[dict]
    summary: dict | None
    seminars: list[dict]
    students: list[dict]
    experiments: list[dict]
    institutions: list[dict]


_PARTS = ('author', 'literature', 'summary', 'seminars', 'students', 'experiments', 'institutions')


def _load(paths: Sequence[Path]) -> Dump:
    """
    Every part comes from the newest dump that has it.

    A dump is the whole state of the author at the time, not a change to an earlier one,
    so older dumps only matter for a part the newest ones were not asked for.
    """
    found: dict[str, Any] = {}
    for path in reversed(paths):  # file names have the date, so the last is the newest
        try:
            data = json.loads(path.read_text(encoding='utf-8'))
        except (OSError, ValueError) as e:
            raise RuntimeError(f'{path}: {e}') from e
        fmt = data.get('format') if isinstance(data, dict) else None
        if fmt != FORMAT:
            raise RuntimeError(f'{path}: dump format {fmt!r}, but this reads {FORMAT}; is HPI or orgface out of date?')
        for part in _PARTS:
            if part in data and part not in found:
                found[part] = data[part]
        if len(found) == len(_PARTS):
            break
    return Dump(
        author=found.get('author'),
        literature=found.get('literature', []),
        summary=found.get('summary'),
        seminars=found.get('seminars', []),
        students=found.get('students', []),
        experiments=found.get('experiments', []),
        institutions=found.get('institutions', []),
    )


@lru_cache(maxsize=4)
def _cached(paths: tuple[Path, ...], stamp: tuple[float, ...]) -> Dump:
    return _load(paths)


def _dump() -> Dump:
    paths = tuple(inputs())
    if len(paths) == 0:
        raise RuntimeError(f'no InspireHEP dumps found in {config.export_path}')
    # the modification times make a dump that was replaced in place be read again
    return _cached(paths, tuple(p.stat().st_mtime for p in paths))


# -- small helpers


def _first(items: Any, key: str) -> Any:
    """The value of ``key`` in the first of a list of objects that has it."""
    for item in items or ():
        if isinstance(item, dict) and item.get(key) is not None:
            return item[key]
    return None


def _ref_id(ref: Any) -> int | None:
    url = ref.get('$ref') if isinstance(ref, dict) else None
    m = re.search(r'/(\d+)$', url or '')
    return int(m.group(1)) if m else None


def _ids(ids: Any) -> dict[str, tuple[str, ...]]:
    by_schema: dict[str, list[str]] = {}
    for i in ids or ():
        by_schema.setdefault(i['schema'], []).append(i['value'])
    return {k: tuple(v) for k, v in by_schema.items()}


def parse_date(text: str | None) -> date | None:
    """
    A date as InspireHEP gives it, which may be only a year or a month.

    >>> parse_date('2022-03-18'), parse_date('2022-03'), parse_date('1993'), parse_date(None)
    (datetime.date(2022, 3, 18), datetime.date(2022, 3, 1), datetime.date(1993, 1, 1), None)
    """
    if not text:
        return None
    parts = [int(p) for p in re.findall(r'\d+', text)[:3]]
    if len(parts) == 0 or not (1 <= parts[0] <= 9999):
        return None
    try:
        return date(parts[0], parts[1] if len(parts) > 1 else 1, parts[2] if len(parts) > 2 else 1)
    except ValueError:
        return None


def _datetime(text: str | None, *, utc: bool = False) -> datetime | None:
    if not text:
        return None
    dt = datetime.fromisoformat(text)
    return dt.replace(tzinfo=UTC) if utc and dt.tzinfo is None else dt


def _records(items: list[dict]) -> dict[int, dict]:
    return {int(r['metadata']['control_number']): r for r in items}


# -- the author


def _author() -> dict:
    author = _dump().author
    if author is None:
        raise RuntimeError('the dumps do not hold the author')
    return author


def profile() -> Res[Profile]:
    try:
        rec = _author()
        m = rec['metadata']
        return Profile(
            recid=int(m['control_number']),
            name=m['name']['value'],
            preferred_name=m['name'].get('preferred_name'),
            status=m.get('status'),
            ids=_ids(m.get('ids')),
            emails=tuple(e['value'] for e in m.get('email_addresses', ())),
            urls=tuple(u['value'] for u in m.get('urls', ())),
            arxiv_categories=tuple(m.get('arxiv_categories', ())),
            native_names=tuple(m['name'].get('native_names', ())) + tuple(m.get('native_names', ())),
            created=_datetime(rec.get('created')),
            updated=_datetime(rec.get('updated')),
        )
    except Exception as e:
        return e


def _institution_location(rec: dict | None) -> str | None:
    if rec is None:
        return None
    addresses: Sequence[dict] = rec['metadata'].get('addresses') or []
    if len(addresses) == 0:
        return None
    a = addresses[0]
    parts = [*(a.get('cities') or ()), a.get('state'), a.get('country')]
    return ', '.join(p for p in parts if p) or None


def _position(p: dict, institutions: dict[int, dict]) -> Position:
    inst_id = _ref_id(p.get('record'))
    rec = institutions.get(inst_id) if inst_id is not None else None
    name = p.get('institution') or (rec['metadata'].get('legacy_ICN') if rec else None) or '?'
    start, end = p.get('start_date'), p.get('end_date')
    return Position(
        institution=name,
        institution_id=inst_id,
        location=_institution_location(rec),
        rank=p.get('rank'),
        start=start,
        end=end,
        start_date=parse_date(start),
        end_date=parse_date(end),
        current=bool(p.get('current', False)),
    )


def positions() -> Iterator[Res[Position]]:
    """All positions, employment and education, most recent first."""
    try:
        institutions = _records(_dump().institutions)
        raw = _author()['metadata'].get('positions', [])
    except Exception as e:
        yield e
        return
    found: list[Position] = []
    for p in raw:
        try:
            found.append(_position(p, institutions))
        except Exception as e:
            yield e
    # still-current first, then newest start; a position without a date goes last
    found.sort(key=lambda p: (not p.current, -(p.start_date or date.min).toordinal()))
    yield from found


def employment() -> Iterator[Res[Position]]:
    for p in positions():
        if isinstance(p, Exception) or not p.is_education:
            yield p


def education() -> Iterator[Res[Position]]:
    for p in positions():
        if isinstance(p, Exception) or p.is_education:
            yield p


def advisors() -> Iterator[Res[Advisor]]:
    try:
        raw = _author()['metadata'].get('advisors', [])
    except Exception as e:
        yield e
        return
    for a in raw:
        try:
            yield Advisor(
                name=a['name'],
                recid=_ref_id(a.get('record')),
                degree_type=a.get('degree_type'),
                ids=_ids(a.get('ids')),
            )
        except Exception as e:
            yield e


# -- experiments and collaborations


def _experiment(rec: dict) -> Experiment:
    m = rec['metadata']
    return Experiment(
        recid=int(m['control_number']),
        name=m.get('legacy_name') or (m.get('experiment') or {}).get('value') or str(m['control_number']),
        long_name=m.get('long_name'),
        collaboration=(m.get('collaboration') or {}).get('value'),
        description=m.get('description'),
        urls=tuple(u['value'] for u in m.get('urls', ())),
        started=m.get('date_started') or m.get('date_proposed'),
        completed=m.get('date_completed'),
        papers=m.get('number_of_papers'),
    )


def experiments() -> Iterator[Res[Experiment]]:
    """Every experiment or collaboration the dumps hold a record of."""
    try:
        raw = _dump().experiments
    except Exception as e:
        yield e
        return
    for rec in raw:
        try:
            yield _experiment(rec)
        except Exception as e:
            yield e


def _experiment_index() -> dict[int, Experiment]:
    return {e.recid: e for e in experiments() if not isinstance(e, Exception)}


def memberships() -> Iterator[Res[Membership]]:
    """The experiments the author's profile says they are, or were, part of."""
    try:
        raw = _author()['metadata'].get('project_membership', [])
        index = _experiment_index()
    except Exception as e:
        yield e
        return
    for p in raw:
        try:
            recid = _ref_id(p.get('record'))
            yield Membership(
                name=p['name'],
                recid=recid,
                current=bool(p.get('current', False)),
                experiment=index.get(recid) if recid is not None else None,
            )
        except Exception as e:
            yield e


def _norm(name: str) -> str:
    """
    The same collaboration is written 'Daya Bay' and 'DAYA-BAY'.

    >>> _norm('Daya Bay') == _norm('DAYA-BAY')
    True
    >>> _norm('MINOS+') == _norm('MINOS')
    False
    """
    return re.sub(r'[\s_.-]+', '', name).casefold()


def collaborations() -> Iterator[Res[Collaboration]]:
    """
    The collaborations and experiments the author is part of, whether the profile or the papers say so.

    The ones with the most papers come first.  The papers do not always give the number of the experiment
    record, so the same collaboration is recognised by its name.
    """
    try:
        index = _experiment_index()
        raw = _dump().literature
        members = list(memberships())
    except Exception as e:
        yield e
        return
    entries: dict[str, dict] = {}  # by normalised name
    for rec in raw:
        try:
            m = rec['metadata']
            when = parse_date(m.get('earliest_date'))
            paper_id = int(m['control_number'])
            for c in m.get('collaborations', ()):
                entry = entries.setdefault(
                    _norm(c['value']),
                    {'name': c['value'], 'recid': None, 'papers': 0, 'first': None, 'last': None, 'paper_ids': {}},
                )
                entry['recid'] = entry['recid'] or _ref_id(c.get('record'))
                if paper_id in entry['paper_ids']:  # a paper that names it twice counts once
                    continue
                entry['paper_ids'][paper_id] = when
                entry['papers'] += 1
                if when is not None:
                    entry['first'] = when if entry['first'] is None else min(entry['first'], when)
                    entry['last'] = when if entry['last'] is None else max(entry['last'], when)
        except Exception as err:
            yield err
    for member in members:
        if isinstance(member, Exception):
            yield member
            continue
        exp = member.experiment
        names = [n for n in ((exp.collaboration, exp.name) if exp else ()) + (member.name,) if n]
        # by name first: papers of MINOS+ cite the record of MINOS
        match = next((entries[_norm(n)] for n in names if _norm(n) in entries), None) or next(
            (x for x in entries.values() if member.recid is not None and x['recid'] == member.recid),
            None,
        )
        if match is None:
            match = entries.setdefault(
                _norm(names[0]),
                {'name': names[0], 'recid': None, 'papers': 0, 'first': None, 'last': None, 'paper_ids': {}},
            )
        match['recid'] = match['recid'] or member.recid
        match['membership'] = member
    found = [
        Collaboration(
            name=entry['name'],
            recid=entry['recid'],
            papers=entry['papers'],
            first=entry['first'],
            last=entry['last'],
            current=entry['membership'].current if 'membership' in entry else None,
            experiment=index.get(entry['recid']) if entry['recid'] is not None else None,
            membership=entry.get('membership'),
            paper_ids=tuple(
                sorted(entry['paper_ids'], key=lambda i: (entry['paper_ids'][i] or date.min, i), reverse=True)
            ),
        )
        for entry in entries.values()
    ]
    found.sort(key=lambda c: (-c.papers, c.name))
    yield from found


# -- papers


def _journal(info: list[dict]) -> str | None:
    for i in info:
        title = i.get('journal_title')
        if not title:
            continue
        text = title
        if i.get('journal_volume'):
            text += f' {i["journal_volume"]}'
        if i.get('year'):
            text += f' ({i["year"]})'
        where = i.get('artid') or i.get('page_start')
        if where:
            text += f' {where}'
        return text
    return None


def _paper(rec: dict) -> Paper:
    m = rec['metadata']
    arxiv = (m.get('arxiv_eprints') or [None])[0]
    first_author = m.get('first_author') or {}
    return Paper(
        recid=int(m['control_number']),
        title=_first(m.get('titles'), 'title') or '(untitled)',
        abstract=_first(m.get('abstracts'), 'value'),
        date=parse_date(m.get('earliest_date')),
        date_text=m.get('earliest_date'),
        document_types=tuple(m.get('document_type', ())),
        arxiv_id=arxiv['value'] if arxiv else None,
        arxiv_category=(arxiv.get('categories') or [None])[0] if arxiv else None,
        dois=tuple(dict.fromkeys(d['value'] for d in m.get('dois', ()))),
        journal=_journal(m.get('publication_info', [])),
        conference=_first(m.get('publication_info'), 'cnum'),
        published=bool(m.get('refereed', False)),
        citations=int(m.get('citation_count', 0)),
        citations_without_self=int(m.get('citation_count_without_self_citations', 0)),
        collaborations=tuple(c['value'] for c in m.get('collaborations', ())),
        experiments=tuple(
            dict.fromkeys(e['legacy_name'] for e in m.get('accelerator_experiments', ()) if 'legacy_name' in e)
        ),
        first_author=first_author.get('full_name'),
        author_count=int(m.get('author_count', 0)),
        keywords=tuple(dict.fromkeys(k['value'] for k in m.get('keywords', ()))),
        categories=tuple(dict.fromkeys(c['term'] for c in m.get('inspire_categories', ()))),
        texkey=(m.get('texkeys') or [None])[0],
        report_numbers=tuple(r['value'] for r in m.get('report_numbers', ())),
        pages=m.get('number_of_pages'),
        urls=tuple(u['value'] for u in m.get('urls', ())),
    )


def papers() -> Iterator[Res[Paper]]:
    """The author's papers, newest first."""
    try:
        raw = _dump().literature
    except Exception as e:
        yield e
        return
    found: list[Paper] = []
    for rec in raw:
        try:
            found.append(_paper(rec))
        except Exception as e:
            yield e
    found.sort(key=lambda p: (p.date or date.min, p.recid), reverse=True)
    yield from found


def citation_summary() -> Res[CitationSummary]:
    try:
        s = _dump().summary
        if s is None:
            return RuntimeError('the dumps hold no citation summary')
        by = s['citations']['buckets']
        all_, pub = by['all'], by['published']
        return CitationSummary(
            papers=int(all_['doc_count']),
            published_papers=int(pub['doc_count']),
            citations=int(all_['citations_count']['value']),
            published_citations=int(pub['citations_count']['value']),
            h_index=int(s['h-index']['value']['all']),
            published_h_index=int(s['h-index']['value']['published']),
            average_citations=all_.get('average_citations', {}).get('value'),
            buckets={b['key']: int(b['doc_count']) for b in all_['citation_buckets']['buckets']},
        )
    except Exception as e:
        return e


# -- seminars and students


def _seminar(rec: dict) -> Seminar:
    m = rec['metadata']
    address = m.get('address') or {}
    venue = (
        ', '.join(p for p in (address.get('place_name'), *(address.get('cities') or ()), address.get('country')) if p)
        or None
    )
    return Seminar(
        recid=int(m['control_number']),
        title=(m.get('title') or {}).get('title') or '(untitled)',
        start=_datetime(m.get('start_datetime'), utc=True),
        end=_datetime(m.get('end_datetime'), utc=True),
        timezone=m.get('timezone'),
        venue=venue,
        series=tuple(s['name'] for s in m.get('series', ()) if 'name' in s),
        abstract=(m.get('abstract') or {}).get('value'),
        urls=tuple(u['value'] for u in m.get('urls', ())),
        categories=tuple(c['term'] for c in m.get('inspire_categories', ())),
    )


def seminars() -> Iterator[Res[Seminar]]:
    """Seminars the author spoke at, newest first."""
    try:
        raw = _dump().seminars
    except Exception as e:
        yield e
        return
    found: list[Seminar] = []
    for rec in raw:
        try:
            found.append(_seminar(rec))
        except Exception as e:
            yield e
    found.sort(key=lambda s: s.start or datetime.min.replace(tzinfo=UTC), reverse=True)
    yield from found


def _student(rec: dict, advisor_id: int) -> Student:
    m = rec['metadata']
    degree = next((a.get('degree_type') for a in m.get('advisors', ()) if _ref_id(a.get('record')) == advisor_id), None)
    study = next((p for p in m.get('positions', ()) if p.get('rank') in {'PHD', 'MASTER', 'UNDERGRADUATE'}), None)
    return Student(
        recid=int(m['control_number']),
        name=m['name']['value'],
        degree_type=degree,
        institution=study.get('institution') if study else None,
        start=study.get('start_date') if study else None,
        end=study.get('end_date') if study else None,
        ids=_ids(m.get('ids')),
    )


def students() -> Iterator[Res[Student]]:
    """People who name the author as an advisor, most recent first."""
    try:
        advisor_id = int(_author()['metadata']['control_number'])
        raw = _dump().students
    except Exception as e:
        yield e
        return
    found: list[Student] = []
    for rec in raw:
        try:
            found.append(_student(rec, advisor_id))
        except Exception as e:
            yield e
    found.sort(key=lambda s: (s.end or s.start or '', s.recid), reverse=True)
    yield from found


def stats() -> Stats:
    return {
        **stat(papers),
        **stat(positions),
        **stat(collaborations),
        **stat(seminars),
        **stat(students),
    }
