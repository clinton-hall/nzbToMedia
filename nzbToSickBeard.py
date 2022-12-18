import sys

import nzbToMedia

SECTION = 'SickBeard'
result = nzbToMedia.main(sys.argv, SECTION)
sys.exit(result)
