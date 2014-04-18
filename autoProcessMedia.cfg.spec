# nzbToMedia Configuration
# For more information, visit https://github.com/clinton-hall/nzbToMedia/wiki

[General]
    version_notify = 1
    auto_update = 0
    git_path =
    git_user =
    git_branch =
    force_clean = 0
    log_debug = 0
    
[CouchPotato]
    #### autoProcessing for Movies
    #### movie - category that gets called for post-processing with CPS
    [[movie]]
        enabled = 0
        apikey =
        host = localhost
        port = 5050
        ###### ADVANCED USE - ONLY EDIT IF YOU KNOW WHAT YOU'RE DOING ######
        ssl = 0
        web_root =
        method = renamer
        delete_failed = 0
        wait_for = 2
        ##### Set to path where completed downloads are found on remote server for this category
        remote_path =
        ##### Set to path where download client places completed downloads locally for this category
        watch_dir =

[SickBeard]
    #### autoProcessing for TV Series
    #### tv - category that gets called for post-processing with SB
    [[tv]]
        enabled = 0
        host = localhost
        port = 8081
        username =
        password =
        ###### ADVANCED USE - ONLY EDIT IF YOU KNOW WHAT YOU'RE DOING ######
        web_root =
        ssl = 0
        fork = auto
        delete_failed = 0
        nzbExtractionBy = Downloader
        Torrent_NoLink = 0
        process_method =
        ##### Set to path where completed downloads are found on remote server for this category
        remote_path =
        ##### Set to path where download client places completed downloads locally for this category
        watch_dir =

[NzbDrone]
    #### autoProcessing for TV Series
    #### ndCategory - category that gets called for post-processing with NzbDrone
    [[tv]]
        enabled = 0
        apikey =
        host = localhost
        port = 8989
        username =
        password =
        ###### ADVANCED USE - ONLY EDIT IF YOU KNOW WHAT YOU'RE DOING ######
        web_root =
        ssl = 0
        delete_failed = 0
        nzbExtractionBy = Downloader
        Torrent_NoLink = 0
        ##### Set to path where completed downloads are found on remote server for this category
        remote_path =
        ##### Set to path where download client places completed downloads locally for this category
        watch_dir =

[HeadPhones]
    #### autoProcessing for Music
    #### music - category that gets called for post-processing with HP
    [[music]]
        enabled = 0
        apikey =
        host = localhost
        port = 8181
        ###### ADVANCED USE - ONLY EDIT IF YOU KNOW WHAT YOU'RE DOING ######
        ssl = 0
        web_root =
        wait_for = 2
        ##### Set to path where completed downloads are found on remote server for this category
        remote_path =
        ##### Set to path where download client places completed downloads locally for this category
        watch_dir =

[Mylar]
    #### autoProcessing for Comics
    #### comics - category that gets called for post-processing with Mylar
    [[comics]]
        enabled = 0
        host = localhost
        port= 8090
        username=
        password=
        ###### ADVANCED USE - ONLY EDIT IF YOU KNOW WHAT YOU'RE DOING ######
        web_root=
        ssl=0
        ##### Set to path where completed downloads are found on remote server for this category
        remote_path =
        ##### Set to path where download client places completed downloads locally for this category
        watch_dir =

[Gamez]
    #### autoProcessing for Games
    #### games - category that gets called for post-processing with Gamez
    [[games]]
        enabled = 0
        apikey =
        host = localhost
        port = 8085
        ###### ADVANCED USE - ONLY EDIT IF YOU KNOW WHAT YOU'RE DOING ######
        ssl = 0
        web_root =
        ##### Set to path where completed downloads are found on remote server for this category
        remote_path =
        ##### Set to path where download client places completed downloads locally for this category
        watch_dir =

[Nzb]
    ###### clientAgent - Supported clients: sabnzbd, nzbget
    clientAgent = sabnzbd
    ###### SabNZBD (You must edit this if your using nzbToMedia.py with SabNZBD)
    sabnzbd_host = localhost
    sabnzbd_port = 8080
    sabnzbd_apikey =

[Torrent]
    ###### clientAgent - Supported clients: utorrent, transmission, deluge, rtorrent, other
    clientAgent = other
    ###### useLink - Set to hard for physical links, sym for symbolic links, move to move, and no to not use links (copy)
    useLink = hard
    ###### outputDirectory - Default output directory (categories will be appended as sub directory to outputDirectory)
    outputDirectory = /abs/path/to/complete/
    ###### Other categories/labels defined for your downloader. Does not include CouchPotato, SickBeard, HeadPhones, Mylar categories.
    categories = music_videos,pictures,software,manual
    ###### A list of categories that you don't want to be flattened (i.e preserve the directory structure when copying/linking.
    noFlatten = pictures,manual
    ###### uTorrent Hardlink solution (You must edit this if your using TorrentToMedia.py with uTorrent)
    uTorrentWEBui = http://localhost:8090/gui/
    uTorrentUSR = your username
    uTorrentPWD = your password
    ###### Transmission (You must edit this if your using TorrentToMedia.py with uTorrent)
    TransmissionHost = localhost
    TransmissionPort = 8084
    TransmissionUSR = your username
    TransmissionPWD = your password
    #### Deluge (You must edit this if your using TorrentToMedia.py with deluge. Note that the host/port is for the deluge daemon, not the webui)
    DelugeHost = localhost
    DelugePort = 58846
    DelugeUSR = your username
    DelugePWD = your password
    ###### ADVANCED USE - ONLY EDIT IF YOU KNOW WHAT YOU'RE DOING ######
    deleteOriginal = 0

[Extensions]
    compressedExtensions = .zip,.rar,.7z,.gz,.bz,.tar,.arj,.1,.01,.001
    mediaExtensions = .mkv,.avi,.divx,.xvid,.mov,.wmv,.mp4,.mpg,.mpeg,.vob,.iso,.m4v
    metaExtensions = .nfo,.sub,.srt,.jpg,.gif
    ###### minSampleSize - Minimum required size to consider a media file not a sample file (in MB, eg 200mb)
    minSampleSize = 200
    ###### SampleIDs - a list of common sample identifiers. Use SizeOnly to ignore this and delete all media files less than minSampleSize
    SampleIDs = sample,-s.

[Transcoder]
    transcode = 0
    ###### duplicate =1 will cretae a new file. =0 will replace the original
    duplicate = 1
    # Only works on Linux. Highest priority is -20, lowest priority is 19.
    niceness = 0
    ignoreExtensions = .avi,.mkv,.mp4
    outputVideoExtension = .mp4
    outputVideoCodec = libx264
    outputVideoPreset = medium
    outputVideoFramerate = 24
    outputVideoBitrate = 800k
    outputAudioCodec = libmp3lame
    outputAudioBitrate = 128k
    outputSubtitleCodec =
    # outputFastStart. 1 will use -movflags + faststart. 0 will disable this from being used.
    outputFastStart = 0
    # outputQualityPercent. used as -q:a value. 0 will disable this from being used.
    outputQualityPercent = 0

[WakeOnLan]
    ###### set wake = 1 to send WOL broadcast to the mac and test the server (e.g. xbmc) the host and port specified.
    wake = 0
    host = 192.168.1.37
    port = 80
    mac = 00:01:2e:2D:64:e1

[UserScript]
    #Use user_script for uncategorized download?
    #Set the categories to use external script, comma separated.
    #Use "UNCAT" to process non-category downloads, and "ALL" for all. Set to "NONE" to disable external script.
    user_script_categories = NONE
    #What extension do you want to process? Specify all the extension, or use "ALL" to process all files.
    user_script_mediaExtensions = .mkv,.avi,.divx,.xvid,.mov,.wmv,.mp4,.mpg,.mpeg
    #Specify the path to your custom script
    user_script_path = /nzbToMedia/userscripts/script.sh
    #Specify the argument(s) passed to script, comma separated in order.
    #for example FP,FN,DN, TN, TL for file path (absolute file name with path), file name, absolute directory name (with path), Torrent Name, Torrent Label/Category.
    #So the result is /media/test/script/script.sh FP FN DN TN TL. Add other arguments as needed eg -f, -r
    user_script_param = FN
    #Set user_script_runOnce = 0 to run for each file, or 1 to only run once (presumably on teh entire directory).
    user_script_runOnce = 0
    #Specify the successcodes returned by the user script as a comma separated list. Linux default is 0
    user_script_successCodes = 0
    #Clean after? Note that delay function is used to prevent possible mistake :) Delay is intended as seconds
    user_script_clean = 1
    delay = 120

[ASCII]
    #Set convert =1 if you want to convert any "foreign" characters to ASCII before passing to SB/CP etc. Default is disabled (0).
    convert = 0

[passwords]
    # enter the full path to a text file containing passwords to be used for extraction attempts.
    # In the passwords file, every password should be on a new line
    PassWordFile =