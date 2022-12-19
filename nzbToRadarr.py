import sys

import nzbToMedia

SECTION = 'Radarr'
result = nzbToMedia.main(sys.argv, SECTION)
sys.exit(result)
