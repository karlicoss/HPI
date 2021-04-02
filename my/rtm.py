"""
[[https://rememberthemilk.com][Remember The Milk]] tasks and notes
"""

REQUIRES = [
    'icalendar',
]

import re
from typing import Dict, List, Iterator
from datetime import datetime

from .common import LazyLogger, get_files, group_by_key, cproperty, make_dict

from my.config import rtm as config


import icalendar # type: ignore
from icalendar.cal import Todo # type: ignore


logger = LazyLogger(__name__)


# TODO extract in a module to parse RTM's ical?
class MyTodo:
    def __init__(self, todo: Todo, revision=None) -> None:
        self.todo = todo
        self.revision = revision

    @cproperty
    def notes(self) -> List[str]:
        # TODO can there be multiple??
        desc = self.todo['DESCRIPTION']
        notes = re.findall(r'---\n\n(.*?)\n\nUpdated:', desc, flags=re.DOTALL)
        return notes

    @cproperty
    def tags(self) -> List[str]:
        desc = self.todo['DESCRIPTION']
        [tags_str] = re.findall(r'\nTags: (.*?)\n', desc, flags=re.DOTALL)
        if tags_str == 'none':
            return []
        tags = [t.strip() for t in tags_str.split(',')]
        return tags

    @cproperty
    def uid(self) -> str:
        return str(self.todo['UID'])

    @cproperty
    def title(self) -> str:
        return str(self.todo['SUMMARY'])

    def get_status(self) -> str:
        if 'STATUS' not in self.todo:
            return None # type: ignore
        # TODO 'COMPLETED'? 
        return str(self.todo['STATUS'])

    # TODO tz?
    @cproperty
    def time(self) -> datetime:
        t1 = self.todo['DTSTAMP'].dt
        t2 = self.todo['LAST-MODIFIED'].dt
        assert t1 == t2 # TODO not sure which one is correct
        return t1

    def is_completed(self) -> bool:
        return self.get_status() == 'COMPLETED'

    def __repr__(self):
        return repr(self.todo)

    def __str__(self):
        return str(self.todo)

    @staticmethod
    def alala_key(mtodo):
        return (mtodo.revision, mtodo.get_time())


class DAL:
    def __init__(self, data: str, revision=None) -> None:
        self.cal = icalendar.Calendar.from_ical(data)
        self.revision = revision

    def all_todos(self) -> Iterator[MyTodo]:
        for t in self.cal.walk('VTODO'):
            yield MyTodo(t, self.revision)

    def get_todos_by_uid(self) -> Dict[str, MyTodo]:
        todos = self.all_todos()
        return make_dict(todos, key=lambda t: t.uid)

    def get_todos_by_title(self) -> Dict[str, List[MyTodo]]:
        todos = self.all_todos()
        return group_by_key(todos, lambda todo: todo.title)


def dal():
    last = get_files(config.export_path)[-1]
    data = last.read_text()
    return DAL(data=data, revision='TODO')


def all_tasks() -> Iterator[MyTodo]:
    yield from dal().all_todos()


def active_tasks() -> Iterator[MyTodo]:
    for t in all_tasks():
        if not t.is_completed():
            yield t


def print_all_todos():
    for t in all_tasks():
        print(t)
