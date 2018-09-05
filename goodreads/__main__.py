from goodreads import get_events

def main():
    for e in get_events():
        print(e)


if __name__ == '__main__':
    main()
