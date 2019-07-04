#!/usr/bin/env python3.6
from config import IGNORED, BACKUPS_PATH
from config import RTM_API_KEY, RTM_API_TOKEN, RTM_API_SECRET

from collections import deque
import logging
import os
import re
from sys import argv

from kython import *

import icalendar # type: ignore
from icalendar.cal import Todo # type: ignore


def extract_backup_date(s: str):
    s = s[len(BACKUPS_PATH + "/rtm_"):-4]
    s = s.replace('_', '-')
    return parse_date(s, dayfirst=False)


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

    def get_notes(self) -> List[str]:
        if self.notes is None:
            self._init_notes()
        return self.notes

    def get_tags(self) -> List[str]:
        if self.tags is None:
            self._init_tags()
        return self.tags

    def get_uid(self) -> str:
        return str(self.todo['UID'])

    def get_title(self) -> str:
        return str(self.todo['SUMMARY'])

    def get_status(self) -> str:
        if 'STATUS' not in self.todo:
            return None # TODO 'COMPLETED'?
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
    def from_path(path: str) -> 'RtmBackup':
        with open(path, 'rb') as fo:
            data = fo.read()
            revision = extract_backup_date(path)
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


# TODO move to kython?
def group_by_any(items: List[T], key1, key2):
    kk1 = group_by_key(items, key1)
    kk2 = group_by_key(items, key2)

    used: Set[T] = set()
    def bfs(i):
        queue = deque()
        res = []
        def register(i):
            if i not in used:
                res.append(i)
                used.add(i)
                queue.append(i)
        register(i)
        while len(queue) > 0:
            top = queue.popleft()
            for ni in kk1[key1(top)]:
                register(ni)
            for ni in kk2[key2(top)]:
                register(ni)
        return res

    groups = []
    for i in items:
        if i not in used:
            groups.append(bfs(i))
    return groups


def check_wiped_notes(backups: List[str]):
    all_todos = []
    for b in backups:
        backup = RtmBackup.from_path(b)
        all_todos.extend(backup.get_all_todos())

    # first, let tasks with same titles or uids be in the same class. (if we rename a task, it retains UID)
    groups = group_by_any(all_todos, lambda k: k.get_title(), lambda k: k.get_uid())
    kk_map = {i: g for i, g in enumerate(groups)} # type: Dict[int, List[MyTodo]]

    def has_safe_tag(todos: List[MyTodo]) -> bool:
        all_tags = set.union(*(set(todo.get_tags()) for todo in todos))
        return 'z_dn_safe' in all_tags or 'y_see_org' in all_tags

    def has_safe_note(todo: MyTodo) -> bool:
        notes = todo.get_notes()
        for note in notes:
            if 'is_safe' in note:
                return True
        return False

    kk_map = {kk: todos for kk, todos in kk_map.items() if not has_safe_tag(todos)}

    def boring(todos: List[MyTodo]) -> bool:
        if len(todos) <= 1:
            return True

        counts = [len(todo.get_notes()) for todo in todos]

        if counts.count(counts[0]) == len(counts):
            return True

        if all(a <= b for a, b in zip(counts, counts[1:])):
            # increasing
            return True

        for tags in [todo.get_tags() for todo in todos]:
            if 'routine' in tags: # TODO FIXME 'safe' tag. If a task has it in ANY of the backups, it is considered safe. tag is better for completed
                return True

        # good thing about safe note is if it disappears, we'll notice it! 
        if has_safe_note(todos[-1]):
            return True

        return False

    bads = []
    for kk, todos in sorted(kk_map.items()):
        # TODO sorts by 1) competion 2) modified date
        todos = sorted(todos, key = MyTodo.alala_key)
        if not boring(todos):
            for todo in todos:
                bads.append(todo)


    if len(bads) != 0:
        logging.error('\n'.join(set(t.get_title() for t in bads)))
        for t in bads:
            logging.error(f"{t.revision} {t.get_title()} {t.get_uid()} {t.get_notes()}")


def are_suspicious(l: List[MyTodo]) -> bool:
    if len(l) <= 1: # probably not repeating
        return False

    all_tags = set.union(*(set(todo.get_tags()) for todo in l))
    if 'z_ac_safe' in all_tags:
        return False

    suspicious = 0
    for c in l:
        if c.is_completed():
            suspicious += 1
        elif 'DUE' not in c.todo:
            suspicious += 1

    return len(l) == suspicious

def check_accidentally_completed(path: str):
    backup = RtmBackup.from_path(path)

    groups = backup.get_todos_by_title()

    susp = []
    for k, g in sorted(groups.items()):
        if k in IGNORED:
            logging.info(k + " is ignored, skipping...")
            continue

        if are_suspicious(g):
            susp.append(f'"{k}",')
            logging.error(k)

    if len(susp) > 0:
        print("Suspicious:")
        for s in susp:
            print(s)
    else:
        print("Nothing suspicious!")


def main():
    backups = sorted([os.path.join(BACKUPS_PATH, p) for p in os.listdir(BACKUPS_PATH) if p.endswith('ical')], key=extract_backup_date)
    last_backup = backups[-1]

    check_accidentally_completed(last_backup)
    logging.info("Using " + last_backup + " for checking for accidentally completed notes")

    backups = backups[:-5:5] + backups[-5:] # always include last 5 # TODO FIXME USE ALL?
    logging.info(f"Using {backups} for checking for wiped notes")

    check_wiped_notes(backups)


if __name__ == '__main__':
    setup_logging()
    main()
