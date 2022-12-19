import sys

import nzbToMedia

SECTION = 'Watcher3'
result = nzbToMedia.main(sys.argv, SECTION)
sys.exit(result)
