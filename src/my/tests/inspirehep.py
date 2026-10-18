import json
from datetime import UTC, date, datetime
from pathlib import Path

import pytest

from my.inspirehep import export


def _ref(collection: str, recid: int) -> dict:
    return {'$ref': f'https://inspirehep.net/api/{collection}/{recid}'}


def _rec(recid: int, **metadata) -> dict:
    return {
        'id': str(recid),
        'created': '2000-01-01T00:00:00+00:00',
        'updated': '2026-01-01T00:00:00+00:00',
        'metadata': {'control_number': recid, **metadata},
    }


AUTHOR = _rec(
    1,
    name={'value': 'Roe, Richard', 'preferred_name': 'Richard Roe'},
    ids=[{'schema': 'ORCID', 'value': '0000-0001-2345-6789'}],
    positions=[
        {
            'institution': 'School',
            'rank': 'PHD',
            'start_date': '1993',
            'end_date': '2000',
            'record': _ref('institutions', 31),
        },
        {
            'institution': 'Lab',
            'rank': 'SENIOR',
            'start_date': '2000',
            'current': True,
            'record': _ref('institutions', 30),
        },
    ],
    advisors=[{'name': 'Poe, Edgar', 'record': _ref('authors', 2), 'degree_type': 'phd'}],
    project_membership=[{'name': 'EXP-1', 'record': _ref('experiments', 20), 'current': True}],
)

DUMP = {
    'format': 1,
    'author': AUTHOR,
    'literature': [
        _rec(
            100,
            titles=[{'title': 'First'}],
            earliest_date='2020-05',
            collaborations=[{'value': 'ExpOne'}],
            publication_info=[{'journal_title': 'JINST', 'journal_volume': '17', 'year': 2022, 'artid': 'P1'}],
            arxiv_eprints=[{'value': '2005.00001', 'categories': ['hep-ex']}],
            dois=[{'value': '10.1/x'}, {'value': '10.1/x'}],
            citation_count=5,
            refereed=True,
        ),
        _rec(
            101,
            titles=[{'title': 'Second'}],
            earliest_date='2022',
            collaborations=[{'value': 'EXP-ONE', 'record': _ref('experiments', 20)}],
        ),
        _rec(102, earliest_date='2021'),  # no title
        {'id': '103', 'metadata': {}},  # no number
    ],
    'summary': {
        'h-index': {'value': {'all': 3, 'published': 2}},
        'citations': {
            'buckets': {
                'all': {
                    'doc_count': 3,
                    'citations_count': {'value': 30.0},
                    'citation_buckets': {'buckets': [{'key': '0--0', 'doc_count': 1}]},
                },
                'published': {'doc_count': 2, 'citations_count': {'value': 20.0}},
            }
        },
    },
    'seminars': [
        _rec(40, title={'title': 'A talk'}, start_datetime='2024-01-02T15:00:00.000000', timezone='Europe/Zurich')
    ],
    'students': [
        _rec(
            3,
            name={'value': 'Moe, Mary'},
            advisors=[{'record': _ref('authors', 1), 'degree_type': 'phd'}],
            positions=[{'institution': 'Lab', 'rank': 'PHD', 'start_date': '2018', 'end_date': '2022'}],
        )
    ],
    'experiments': [_rec(20, legacy_name='EXP-1', long_name='Experiment One', collaboration={'value': 'ExpOne'})],
    'institutions': [
        _rec(30, legacy_ICN='Lab', addresses=[{'cities': ['Town'], 'state': 'ST', 'country': 'Nowhere'}]),
        _rec(31, legacy_ICN='School'),
    ],
}


@pytest.fixture
def dumps(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    directory = tmp_path / 'dumps'
    directory.mkdir()
    (directory / 'inspirehep-2026-10-18.json').write_text(json.dumps(DUMP))
    monkeypatch.setattr(export.config, 'export_path', directory)
    export._cached.cache_clear()
    return directory


def test_parse_date() -> None:
    assert export.parse_date('2022-03-18') == date(2022, 3, 18)
    assert export.parse_date('2022-03') == date(2022, 3, 1)
    assert export.parse_date('1993') == date(1993, 1, 1)
    assert export.parse_date('garbage') is None
    assert export.parse_date('2022-13-45') is None
    assert export.parse_date(None) is None


def test_profile(dumps: Path) -> None:
    me = export.profile()
    assert not isinstance(me, Exception)
    assert me.name == 'Roe, Richard'
    assert me.ids == {'ORCID': ('0000-0001-2345-6789',)}
    assert me.url == 'https://inspirehep.net/authors/1'
    assert me.created == datetime(2000, 1, 1, tzinfo=UTC)


def test_employment_and_education_are_told_apart(dumps: Path) -> None:
    [job] = list(export.employment())
    [school] = list(export.education())
    assert not isinstance(job, Exception)
    assert not isinstance(school, Exception)
    assert (job.institution, job.rank, job.current, job.location) == ('Lab', 'SENIOR', True, 'Town, ST, Nowhere')
    assert (school.institution, school.start_date, school.end_date) == ('School', date(1993, 1, 1), date(2000, 1, 1))
    assert [p.institution for p in export.positions() if not isinstance(p, Exception)] == ['Lab', 'School']


def test_advisors(dumps: Path) -> None:
    [advisor] = list(export.advisors())
    assert not isinstance(advisor, Exception)
    assert (advisor.name, advisor.recid, advisor.degree_type) == ('Poe, Edgar', 2, 'phd')


def test_papers_newest_first_and_a_bad_one_is_an_error_not_a_loss(dumps: Path) -> None:
    results = list(export.papers())
    errors = [r for r in results if isinstance(r, Exception)]
    papers = [r for r in results if not isinstance(r, Exception)]
    assert len(errors) == 1  # the one with no number
    assert [p.title for p in papers] == ['Second', '(untitled)', 'First']
    first = papers[-1]
    assert first.date == date(2020, 5, 1)
    assert first.date_text == '2020-05'
    assert first.journal == 'JINST 17 (2022) P1'
    assert first.dois == ('10.1/x',)
    assert (first.arxiv_id, first.arxiv_category, first.published, first.citations) == ('2005.00001', 'hep-ex', True, 5)
    assert first.doi_url == 'https://doi.org/10.1/x'
    assert first.arxiv_url == 'https://arxiv.org/abs/2005.00001'


def test_collaborations_join_the_profile_and_the_papers_by_name(dumps: Path) -> None:
    [c] = [c for c in export.collaborations() if not isinstance(c, Exception)]
    assert c.name == 'ExpOne'  # 'EXP-ONE' on the other paper is the same
    assert c.papers == 2
    assert (c.first, c.last) == (date(2020, 5, 1), date(2022, 1, 1))
    assert c.current is True
    assert c.recid == 20
    assert c.experiment is not None
    assert c.experiment.long_name == 'Experiment One'
    assert c.membership is not None
    assert c.membership.name == 'EXP-1'


def test_citation_summary(dumps: Path) -> None:
    s = export.citation_summary()
    assert not isinstance(s, Exception)
    assert (s.h_index, s.published_h_index, s.citations, s.papers) == (3, 2, 30, 3)
    assert s.buckets == {'0--0': 1}


def test_seminars_and_students(dumps: Path) -> None:
    [seminar] = list(export.seminars())
    [student] = list(export.students())
    assert not isinstance(seminar, Exception)
    assert not isinstance(student, Exception)
    assert seminar.title == 'A talk'
    assert seminar.start == datetime(2024, 1, 2, 15, tzinfo=UTC)
    assert (student.name, student.degree_type, student.institution, student.end) == ('Moe, Mary', 'phd', 'Lab', '2022')


def test_the_newest_dump_that_has_a_part_wins_that_part(dumps: Path) -> None:
    older = {**DUMP, 'literature': DUMP['literature'][:1]}
    (dumps / 'inspirehep-2026-10-01.json').write_text(json.dumps(older))
    newer = {
        'format': 1,
        'author': {**AUTHOR, 'metadata': {**AUTHOR['metadata'], 'status': 'retired'}},
    }  # only the author
    (dumps / 'inspirehep-2026-10-19.json').write_text(json.dumps(newer))
    export._cached.cache_clear()
    me = export.profile()
    assert not isinstance(me, Exception)
    assert me.status == 'retired'
    assert len([p for p in export.papers() if not isinstance(p, Exception)]) == 3  # from 10-18, not the older 10-01


def test_a_dump_of_another_format_is_refused_by_name(dumps: Path) -> None:
    (dumps / 'inspirehep-2026-10-19.json').write_text(json.dumps({'format': 99}))
    export._cached.cache_clear()
    me = export.profile()
    assert isinstance(me, Exception)
    assert 'inspirehep-2026-10-19.json' in str(me)
    assert '99' in str(me)


def test_no_dumps_say_so(dumps: Path) -> None:
    for f in dumps.iterdir():
        f.unlink()
    export._cached.cache_clear()
    me = export.profile()
    assert isinstance(me, Exception)
    assert 'no InspireHEP dumps' in str(me)


def test_a_replaced_dump_is_read_again(dumps: Path) -> None:
    assert len(list(export.papers())) == 4
    path = dumps / 'inspirehep-2026-10-18.json'
    path.write_text(json.dumps({**DUMP, 'literature': DUMP['literature'][:1]}))
    import os

    os.utime(path, (1, 1_900_000_000))
    assert len(list(export.papers())) == 1
