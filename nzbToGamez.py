import sys

import nzbToMedia

SECTION = 'Gamez'
result = nzbToMedia.main(sys.argv, SECTION)
sys.exit(result)
