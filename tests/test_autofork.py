from autoProcess.nzbToMediaUtil import *
from autoProcess.autoSickBeardFork import autoFork
nzbtomedia_configure_logging(LOG_FILE)

fork, params = autoFork()
print fork, params