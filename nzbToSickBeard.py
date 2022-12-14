import sys

import nzbToMedia

section = 'SickBeard'
result = nzbToMedia.main(sys.argv, section)
sys.exit(result)
