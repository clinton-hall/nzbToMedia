# Make things easy and less error prone by centralising all common values

# Global Constants
VERSION = 'V8.6'

# Constants pertinant to SabNzb
SABNZB_NO_OF_ARGUMENTS = 8

# Constants pertaining to SickBeard Branches: 
# extend this list to include all branches/forks that use "failed" to handle failed downloads.
SICKBEARD_FAILED = ["failed", "TPB-failed", "Pistachitos", "TPB"]
# extend this list to include all branches/forks that use "dirName" not "dir"
SICKBEARD_DIRNAME = ["failed"] 
# extend this list to include all branches/forks that process rar and link files for torrents and therefore skip extraction and linking in TorrentToMedia.
SICKBEARD_TORRENT = ["TPB", "TPB-failed", "Pistachitos"]


