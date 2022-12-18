import sys

import nzbToMedia

SECTION = 'NzbDrone'
result = nzbToMedia.main(sys.argv, SECTION)
sys.exit(result)
