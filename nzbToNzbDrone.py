import sys

import nzbToMedia

section = 'NzbDrone'
result = nzbToMedia.main(sys.argv, section)
sys.exit(result)
