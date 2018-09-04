from github import get_events

for e in get_events():
    print(e)
