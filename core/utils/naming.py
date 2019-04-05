import re
import core


def sanitize_name(name):
    """
    >>> sanitize_name('a/b/c')
    'a-b-c'
    >>> sanitize_name('abc')
    'abc'
    >>> sanitize_name('a"b')
    'ab'
    >>> sanitize_name('.a.b..')
    'a.b'
    """

    # remove bad chars from the filename
    name = re.sub(r'[\\/*]', '-', name)
    name = re.sub(r'[:\'<>|?]', '', name)

    # remove leading/trailing periods and spaces
    name = name.strip(' .')
    # try:
    #    name = name.encode(core.SYS_ENCODING)
    # except Exception:
    #    pass

    return name


def clean_file_name(filename):
    """Cleans up nzb name by removing any . and _
    characters, along with any trailing hyphens.

    Is basically equivalent to replacing all _ and . with a
    space, but handles decimal numbers in string, for example:
    """

    filename = re.sub(r'(\D)\.(?!\s)(\D)', r'\1 \2', filename)
    filename = re.sub(r'(\d)\.(\d{4})', r'\1 \2', filename)  # if it ends in a year then don't keep the dot
    filename = re.sub(r'(\D)\.(?!\s)', r'\1 ', filename)
    filename = re.sub(r'\.(?!\s)(\D)', r' \1', filename)
    filename = filename.replace('_', ' ')
    filename = re.sub('-$', '', filename)
    filename = re.sub(r'^\[.*]', '', filename)
    return filename.strip()


def is_sample(input_name):
    # Ignore 'sample' in files
    if re.search('(^|[\\W_])sample\\d*[\\W_]', input_name.lower()):
        return True
