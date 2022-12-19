import sys

import nzbToMedia

SECTION = 'Lidarr'
result = nzbToMedia.main(sys.argv, SECTION)
sys.exit(result)
