import traceback
import sys
import logging

from jaraco.windows.filesystem import change

logging.basicConfig(level=logging.INFO)


def long_handler(file):
    try:
        with open(file, 'rb') as f:
            data = f.read()
        print("read", len(data), "bytes from", file)
    except Exception:
        traceback.print_exc()


def main():
    try:
        watch()
    except KeyboardInterrupt:
        pass


def watch():
    notifier = change.BlockingNotifier(sys.argv[1])
    notifier.watch_subtree = True

    for ch in notifier.get_changed_files():
        long_handler(ch)


if __name__ == '__main__':
    main()
