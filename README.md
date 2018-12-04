nzbToMedia
================

Provides an [efficient](https://github.com/clinton-hall/nzbToMedia/wiki/Efficient-on-demand-post-processing) way to handle postprocessing for [CouchPotatoServer](https://couchpota.to/ "CouchPotatoServer") and [SickBeard](http://sickbeard.com/ "SickBeard") (and its [forks](https://github.com/clinton-hall/nzbToMedia/wiki/Failed-Download-Handling-%28FDH%29#sick-beard-and-its-forks))
when using one of the popular NZB download clients like [SABnzbd](http://sabnzbd.org/ "SABnzbd") and [NZBGet](http://nzbget.sourceforge.net/ "NZBGet") on low performance systems like a NAS. 
This script is based on sabToSickBeard (written by Nic Wolfe and supplied with SickBeard), with the support for NZBGet being added by [thorli](https://github.com/thorli "thorli") and further contributions by [schumi2004](https://github.com/schumi2004 "schumi2004") and [hugbug](https://sourceforge.net/apps/phpbb/nzbget/memberlist.php?mode=viewprofile&u=67 "hugbug").
Torrent suport added by [jkaberg](https://github.com/jkaberg "jkaberg") and [berkona](https://github.com/berkona "berkona")
Corrupt video checking, auto SickBeard fork determination and a whole lot of code improvement was done by [echel0n](https://github.com/echel0n "echel0n")

Introduction
------------
Originally this was modified from the SickBeard version to allow for ["on-demand" renaming](https://github.com/clinton-hall/nzbToMedia/wiki/Efficient-on-demand-post-processing) and not have My QNAP TS-412 NAS constantly scanning the download directory. 
Later, a few failed downloads prompted me to incorporate ["failed download" handling](https://github.com/clinton-hall/nzbToMedia/wiki/Failed-Download-Handling-%28FDH%29).
Failed download handling is now provided for SABnzbd, by CouchPotatoServer; however on arm processors (e.g. small NAS systems) this can be un-reliable.

Failed download handling for SickBeard is available by using Tolstyak's fork [SickBeard-failed](https://github.com/hugepants/Sick-Beard)).
To use this feature, in autoProcessTV.cfg set the parameter "fork=failed". Default is "fork=default" and will work with the standard version of SickBeard and just ignores failed downloads.
Development of Tolstyak's fork ended in 2013, but newer forks exist with significant feature updates such as [Mr-Orange TPB](https://github.com/coach0742/Sick-Beard) (discontinued), [SickRageTV](https://github.com/SiCKRAGETV/SickRage) and [SickRage](https://github.com/SickRage/SickRage) (active). See [SickBeard Forks](https://github.com/clinton-hall/nzbToMedia/wiki/Failed-Download-Handling-%28FDH%29#sick-beard-and-its-forks "SickBeard Forks") for a list of known forks.

Full support is provided for [SickRageTV](https://github.com/SiCKRAGETV/SickRage), [SickRage](https://github.com/SickRage/SickRage), and [SickGear](https://github.com/SickGear/SickGear).

Torrent support has been added with the assistance of jkaberg and berkona. Currently supports uTorrent, Transmission, Deluge and possibly more.
To enable Torrent extraction, on Windows, you need to install [7-zip](http://www.7-zip.org/ "7-zip") or on *nix you need to install the following packages/commands.
	
	"unrar", "unzip", "tar", "7zr"
	note: "7zr" is available from the p7zip package. Available on Optware.

In order to use the transcoding option, and corrupt video checking you will need to install ffmpeg (and ffprobe).
Installation instructions for this are available in the [wiki](https://github.com/clinton-hall/nzbToMedia/wiki/Transcoder "wiki")
	
Contribution
------------
We who have developed nzbToMedia believe in the openness of open-source, and as such we hope that any modifications will lead back to the [orignal repo](https://github.com/clinton-hall/nzbToMedia "orignal repo") via pull requests.

Founder: [clinton-hall](https://github.com/clinton-hall "clinton-hall")

Contributors: Can be viewed [here](https://github.com/clinton-hall/nzbToMedia/contributors "here")


Installation
------------

**See more detailed instructions in the [wiki](https://github.com/clinton-hall/nzbToMedia/wiki "wiki")** 

### Windows

Support of the compiled versions of this code has ceased. Compiling this expanding code is becoming very difficult and time-consuming. Installing Python and running from source is not too complex. Please follow the instructions on the Wiki link above.
Sorry for any inconvenience caused here.


### General

1. Install python 2.7.

2. Clone or copy all files into a directory wherever you want to keep them (eg. /scripts/ in the home directory of your download client) 
   and change the permission accordingly so the download client can access these files.
	
  `git clone git://github.com/clinton-hall/nzbToMedia.git`

### Configuration

1. Please read the [wiki](https://github.com/clinton-hall/nzbToMedia/wiki "wiki") pages for configuration settings appropriate to your system.

2. Please add to the wiki pages to help assist others ;)

### Issues

1. Please report all issues, or potential enhancements using the [issues](https://github.com/clinton-hall/nzbToMedia/issues "issues") page on this repo.
