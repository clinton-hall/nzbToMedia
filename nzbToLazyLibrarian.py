import sys

import nzbToMedia

section = 'LazyLibrarian'
result = nzbToMedia.main(sys.argv, section)
sys.exit(result)
