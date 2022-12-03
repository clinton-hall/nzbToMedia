from jaraco.windows.api.filesystem import ReplaceFile

open('orig-file', 'w').write('some content')
open('replacing-file', 'w').write('new content')
ReplaceFile('orig-file', 'replacing-file', 'orig-backup', 0, 0, 0)
assert open('orig-file').read() == 'new content'
assert open('orig-backup').read() == 'some content'
import os

assert not os.path.exists('replacing-file')
