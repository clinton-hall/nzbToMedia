import sys

import nzbToMedia

SECTION = 'Mylar'
result = nzbToMedia.main(sys.argv, SECTION)
sys.exit(result)
