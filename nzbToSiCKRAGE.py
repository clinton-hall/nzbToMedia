import sys

import nzbToMedia

SECTION = 'SiCKRAGE'
result = nzbToMedia.main(sys.argv, SECTION)
sys.exit(result)
