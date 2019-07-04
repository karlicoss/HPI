#!/usr/bin/env python3
# pip3 install icalendar
import logging
import os
import re
from collections import deque
from pathlib import Path
from sys import argv
from typing import Dict, List, Optional, TypeVar

from kython.klogging import LazyLogger
from kython import group_by_key
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
        self.notes = None
        self.tags = None
        self.revision = revision

    def _init_notes(self):
        desc = self.todo['DESCRIPTION']
        self.notes = re.findall(r'---\n\n(.*?)\n\nUpdated:', desc, flags=re.DOTALL)

    def _init_tags(self):
        desc = self.todo['DESCRIPTION']
        [tags_str] = re.findall(r'\nTags:(.*?)\n', desc, flags=re.DOTALL)
        self.tags = [t.strip() for t in tags_str.split(',')] # TODO handle none?

    # TODO use caching wrapper
    # TODO use decorator that stores cache in the object itself?
    def get_notes(self) -> List[str]:
        if self.notes is None:
            self._init_notes()
        return self.notes # type: ignore

    def get_tags(self) -> List[str]:
        if self.tags is None:
            self._init_tags()
        return self.tags # type: ignore

    def get_uid(self) -> str:
        return str(self.todo['UID'])

    def get_title(self) -> str:
        return str(self.todo['SUMMARY'])

    def get_status(self) -> str:
        if 'STATUS' not in self.todo:
            return None # type: ignore
        # TODO 'COMPLETED'? 
        return str(self.todo['STATUS'])

    def get_time(self):
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
        res = {todo.get_uid(): todo for todo in todos}
        assert len(res) == len(todos) # hope uid is unique, but just in case
        return res

    def get_todos_by_title(self) -> Dict[str, List[MyTodo]]:
        todos = self.get_all_todos()
        return group_by_key(todos, lambda todo: todo.get_title())


def main():
    backup = RtmBackup.from_path(get_last_backup())
    for t in backup.get_all_todos():
        print(t)


if __name__ == '__main__':
    main()
