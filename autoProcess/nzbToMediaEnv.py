# Make things easy and less error prone by centralising all common values

# Global Constants
VERSION = 'V9.2'
TimeOut = 60

# Constants pertinant to SabNzb
SABNZB_NO_OF_ARGUMENTS = 8
SABNZB_0717_NO_OF_ARGUMENTS = 9

# Constants pertaining to SickBeard Branches:
fork_default = "default"
fork_failed = "failed"
fork_failed_torrent = "failed-torrent"

forks = {}
forks[fork_default] = {"dir": None, "process": None}
forks[fork_failed] = {"dir": None, "failed": None}
forks[fork_failed_torrent] = {"dir": None, "failed": None, "process_method": None}

SICKBEARD_FAILED = [fork_failed, fork_failed_torrent]
SICKBEARD_TORRENT = [fork_failed_torrent]

