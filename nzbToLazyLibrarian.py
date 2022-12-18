import sys

import nzbToMedia

SECTION = 'LazyLibrarian'
result = nzbToMedia.main(sys.argv, SECTION)
sys.exit(result)
