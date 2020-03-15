#!/usr/bin/env python3
# pip3 install icalendar
import logging
import os
import re
from collections import deque
from pathlib import Path
from sys import argv
from typing import Dict, List, Optional, TypeVar
from datetime import datetime

from kython.klogging import LazyLogger
from kython import group_by_key, cproperty
from kython import kompress

import icalendar # type: ignore
from icalendar.cal import Todo # type: ignore


logger = LazyLogger('rtm-provider')


def get_last_backup():
    return max(Path('***REMOVED***').glob('*.ical*'))


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


class RtmBackup:
    def __init__(self, data: bytes, revision=None) -> None:
        self.cal = icalendar.Calendar.from_ical(data)
        self.revision = revision

    @staticmethod
    def from_path(path: Path) -> 'RtmBackup':
        with kompress.open(path, 'rb') as fo:
            data = fo.read()
            revision = 'TODO FIXME' # extract_backup_date(path)
            return RtmBackup(data, revision)

    def get_all_todos(self) -> List[MyTodo]:
        return [MyTodo(t, self.revision) for t in self.cal.walk('VTODO')]

    def get_todos_by_uid(self) -> Dict[str, MyTodo]:
        todos = self.get_all_todos()
        res = {todo.uid: todo for todo in todos}
        assert len(res) == len(todos) # hope uid is unique, but just in case
        return res

    def get_todos_by_title(self) -> Dict[str, List[MyTodo]]:
        todos = self.get_all_todos()
        return group_by_key(todos, lambda todo: todo.title)


def get_all_tasks():
    b = RtmBackup.from_path(get_last_backup())
    return b.get_all_todos()


def get_active_tasks():
    return [t for t in get_all_tasks() if not t.is_completed()]


def test():
    tasks = get_all_tasks()
    assert len([t for t in tasks if 'gluons' in t.title]) > 0


def main():
    backup = RtmBackup.from_path(get_last_backup())
    for t in backup.get_all_todos():
        print(t)


if __name__ == '__main__':
    main()
