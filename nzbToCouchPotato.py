import sys

import nzbToMedia

SECTION = 'CouchPotato'
result = nzbToMedia.main(sys.argv, SECTION)
sys.exit(result)
