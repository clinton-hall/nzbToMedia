from jaraco.windows.filesystem import trace_symlink_target

from optparse import OptionParser


def get_args():
    parser = OptionParser()
    options, args = parser.parse_args()
    try:
        options.filename = args.pop(0)
    except IndexError:
        parser.error('filename required')
    return options


def main():
    options = get_args()
    print(trace_symlink_target(options.filename))


if __name__ == '__main__':
    main()
