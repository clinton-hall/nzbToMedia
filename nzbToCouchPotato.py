#!/usr/bin/env python

import sys
import autoProcessMovie 

if len(sys.argv) < 8:
	print "Invalid number of arguments received from client. Please update it."
	sys.exit()
else:
	print "Script triggered from client, starting autoProcessMovie..."
	autoProcessMovie.process(sys.argv[1], sys.argv[2], sys.argv[7])

# sys.argv:
# 1	The final directory of the job (full path)
# 2	The original name of the NZB file
# 3	Clean version of the job name (no path info and ".nzb" removed)
# 4	Indexer's report number (if supported)
# 5	User-defined category
# 6	Group that the NZB was posted in e.g. alt.binaries.x
# 7	Status of post processing. 0 = OK, 1=failed verification, 2=failed unpack, 3=1+2
