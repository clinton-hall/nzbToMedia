import os


def findpath(target, start=os.path.curdir):
    r"""
    Find a path from start to target where target is relative to start.

    >>> orig_wd = os.getcwd()
    >>> os.chdir('c:\\windows') # so we know what the working directory is

    >>> findpath('d:\\')
    'd:\\'

    >>> findpath('d:\\', 'c:\\windows')
    'd:\\'

    >>> findpath('\\bar', 'd:\\')
    'd:\\bar'

    >>> findpath('\\bar', 'd:\\foo') # fails with '\\bar'
    'd:\\bar'

    >>> findpath('bar', 'd:\\foo')
    'd:\\foo\\bar'

    >>> findpath('bar\\baz', 'd:\\foo')
    'd:\\foo\\bar\\baz'

    >>> findpath('\\baz', 'd:\\foo\\bar') # fails with '\\baz'
    'd:\\baz'

    Since we're on the C drive, findpath may be allowed to return
    relative paths for targets on the same drive. I use abspath to
    confirm that the ultimate target is what we expect.
    >>> os.path.abspath(findpath('\\bar'))
    'c:\\bar'

    >>> os.path.abspath(findpath('bar'))
    'c:\\windows\\bar'

    >>> findpath('..', 'd:\\foo\\bar')
    'd:\\foo'

    >>> findpath('..\\bar', 'd:\\foo')
    'd:\\bar'

    The parent of the root directory is the root directory.
    >>> findpath('..', 'd:\\')
    'd:\\'

    restore the original working directory
    >>> os.chdir(orig_wd)
    """
    return os.path.normpath(os.path.join(start, target))


def main():
    import sys

    if sys.argv[1:]:
        print(findpath(*sys.argv[1:]))
    else:
        import doctest

        doctest.testmod()


if __name__ == '__main__':
    main()
