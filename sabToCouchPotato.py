#!/usr/bin/env python

import sys
import autoProcessMovie 

if len(sys.argv) < 2: 
    print "Not enough arguments received from NZBGet." 
    print "Running autoProcessMovie as a manual run"
    autoProcessMovie.process('Manual Run', 'Manual Run', 0)
else:
    status = 0
    autoProcessMovie.process(sys.argv[1], sys.argv[2], status)


# NZBGet argv: 
# 1  The final directory of the job (full path) 
# 2  The original name of the NZB file 
# 3  Status of post processing. 0 = OK


