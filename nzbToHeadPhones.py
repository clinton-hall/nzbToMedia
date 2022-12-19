import sys

import nzbToMedia

SECTION = 'HeadPhones'
result = nzbToMedia.main(sys.argv, SECTION)
sys.exit(result)
