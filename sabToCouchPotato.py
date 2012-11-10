#!/usr/bin/env python

import sys
import autoProcessMovie 

if len(sys.argv) < 8: 
    print "Not enough arguments received from SABnzbd." 
    print "Running autoProcessMovie as a manual run"
    autoProcessMovie.process('Manual Run', 'Manual Run', 0)
else:
    status = int(sys.argv[7])
    autoProcessMovie.process(sys.argv[1], sys.argv[2], status)


# SABnzbd argv: 
# 1  The final directory of the job (full path) 
# 2  The original name of the NZB file 
# 3  Clean version of the job name (no path info and ".nzb" removed) 
# 4  Indexer's report number (if supported) 
# 5  User-defined category 
# 6  Group that the NZB was posted in e.g. alt.binaries.x 
# 7  Status of post processing. 0 = OK, 1=failed verification, 2=failed unpack, 3=1+2


