#!/usr/bin/env python
#
##############################################################################
### NZBGET POST-PROCESSING SCRIPT                                          ###

# Post-Process to CouchPotato, SickBeard, NzbDrone, Mylar, Gamez, HeadPhones.
#
# This script sends the download to your automated media management servers.
#
# NOTE: This script requires Python to be installed on your system.

##############################################################################
#
### OPTIONS                                                                ###

## General

# Auto Update nzbToMedia (0, 1).
#
# Set to 1 if you want nzbToMedia to automatically check for and update to the latest version
#auto_update=0

## Gamez

# Gamez script category.
#
# category that gets called for post-processing with Gamez.
#gzCategory=games

# Gamez api key.
#gzapikey=

# Gamez host.
#gzhost=localhost

# Gamez port.
#gzport=8085

# Gamez uses ssl (0, 1).
#
# Set to 1 if using ssl, else set to 0.
#gzssl=0

# Gamez web_root
#
# set this if using a reverse proxy.
#gzweb_root=

## WakeOnLan

# use WOL (0, 1).
#
# set to 1 to send WOL broadcast to the mac and test the server (e.g. xbmc) on the host and port specified.
#wolwake=0

# WOL MAC
#
# enter the mac address of the system to be woken.
#wolmac=00:01:2e:2D:64:e1

# Set the Host and Port of a server to verify system has woken.
#wolhost=192.168.1.37
#wolport=80

### NZBGET POST-PROCESSING SCRIPT                                          ###
##############################################################################

# Stub file to call nzbToMedia
import nzbToMedia

def main():
    # call nzbToMedia
    nzbToMedia.main()

if __name__ == "__main__":
    exit(main())
