import sys

import nzbToMedia

section = 'CouchPotato'
result = nzbToMedia.main(sys.argv, section)
sys.exit(result)
