# Make things easy and less error prone by centralising all common values

# Global Constants
VERSION = 'V9.3'
TimeOut = 60

# Constants pertinant to SabNzb
SABNZB_NO_OF_ARGUMENTS = 8
SABNZB_0717_NO_OF_ARGUMENTS = 9

# Constants pertaining to SickBeard Branches:
fork_default = "default"
fork_default_new = "default-new"
fork_failed = "failed"
fork_failed_new = "failed-new"
fork_failed_torrent = "failed-torrent"

forks = {} # these need to be in order of most unique params first.
forks[1] = {'name': fork_failed_torrent, 'params': {"dir": None, "failed": None, "process_method": None}}
forks[2] = {'name': fork_failed, 'params': {"dirName": None, "failed": None}}
forks[3] = {'name': fork_failed_new, 'params': {"dir": None, "failed": None}}
forks[4] = {'name': fork_default_new, 'params': {"dir": None, "process": None}}
forks[5] = {'name': fork_default, 'params': {"dir": None}}

SICKBEARD_FAILED = [fork_failed, fork_failed_torrent, fork_failed_new]
SICKBEARD_TORRENT = [fork_failed_torrent]

