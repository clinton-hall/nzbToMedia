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

forks = {}
forks[fork_failed_torrent] = {"dir": None, "failed": None, "process_method": None}
forks[fork_failed] = {"dirName": None, "failed": None}
forks[fork_failed_new] = {"dir": None, "failed": None}
forks[fork_default_new] = {"dir": None, "process": None}
forks[fork_default] = {"dir": None}

SICKBEARD_FAILED = [fork_failed, fork_failed_torrent, fork_failed_new]
SICKBEARD_TORRENT = [fork_failed_torrent]

