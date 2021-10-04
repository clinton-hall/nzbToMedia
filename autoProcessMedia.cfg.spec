# nzbToMedia Configuration
# For more information, visit https://github.com/clinton-hall/nzbToMedia/wiki

[General]
    # Enable/Disable update notifications
    version_notify = 1
    # Enable/Disable automatic updates
    auto_update = 0
    # Set to the full path to the git executable
    git_path =
    # GitHUB user for repo
    git_user =
    # GitHUB branch for repo
    git_branch =
    # Enable/Disable forceful cleaning of leftover files following postprocess
    force_clean = 0
    # Enable/Disable logging debug messages to nzbtomedia.log
    log_debug = 0
    # Enable/Disable logging database messages to nzbtomedia.log
    log_db = 0
    # Enable/Disable logging environment variables to debug nzbtomedia.log (helpful to track down errors calling external tools.)
    log_env = 0
    # Enable/Disable logging git output to debug nzbtomedia.log (helpful to track down update failures.)
    log_git = 0
    # Set to the directory to search for executables if not in default system path
    sys_path =
    # Set to the directory where your ffmpeg/ffprobe executables are located
    ffmpeg_path =
    # Enable/Disable media file checking using ffprobe.
    check_media = 1
    # Required media audio language for media to be deemed valid. Leave blank to disregard media audio language check.
    require_lan = 
    # Enable/Disable a safety check to ensure we don't process all downloads in the default_downloadDirectories by mistake.
    safe_mode = 1
    # Turn this on to disable additional extraction attempts for failed downloads. Default = 0 will attempt to extract and verify if media is present.
    no_extract_failed = 0

[Posix]
    ### Process priority setting for External commands (Extractor and Transcoder) on Posix (Unix/Linux/OSX) systems.
    # Set the Niceness value for the nice command. These range from -20 (most favorable to the process) to 19 (least favorable to the process).
    # If entering an integer e.g 'niceness = 4', this is added to the nice command and passed as 'nice -n4' (Default).
    # If entering a comma separated list e.g. 'niceness = nice,4' this will be passed as 'nice 4' (Safer).
    niceness = nice,-n0
    # Set the ionice scheduling class. 0 for none, 1 for real time, 2 for best-effort, 3 for idle.
    ionice_class = 0
    # Set the ionice scheduling class data. This defines the class data, if the class accepts an argument. For real time and best-effort, 0-7 is valid data.
    ionice_classdata = 0

[Windows]
    ### Set specific settings for Windows systems
    # Set this to 1 to allow extraction (7zip) windows to be lunched visble (for debugging) otherwise 0 to have this run in background.
    show_extraction = 0

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
        # api key for www.omdbapi.com (used as alternative to imdb)
        omdbapikey =
        # Enable/Disable linking for Torrents
        Torrent_NoLink = 0
        keep_archive = 1
        method = renamer
        delete_failed = 0
        wait_for = 2
        # Set this to suppress error if no status change after rename called
        no_status_check = 0
        extract = 1
        # Set this to minimum required size to consider a media file valid (in MB)
        minSize = 0
        # Enable/Disable deleting ignored files (samples and invalid media files)
        delete_ignored = 0
        ##### Enable if Couchpotato is on a remote server for this category
        remote_path = 0
        ##### Set to path where download client places completed downloads locally for this category
        watch_dir =
        ##### Set the recursive directory permissions to the following (0 to disable)
        chmodDirectory = 0

[Radarr]
    #### autoProcessing for Movies
    #### raCategory - category that gets called for post-processing with Radarr
    [[movie]]
        enabled = 0
        apikey =
        host = localhost
        port = 7878
        ###### ADVANCED USE - ONLY EDIT IF YOU KNOW WHAT YOU'RE DOING ######
        web_root =
        ssl = 0
        # api key for www.omdbapi.com (used as alternative to imdb)
        omdbapikey =
        delete_failed = 0
        # Enable/Disable linking for Torrents
        Torrent_NoLink = 0
        keep_archive = 1
        extract = 1
        nzbExtractionBy = Downloader
        wait_for = 6
        # Set this to minimum required size to consider a media file valid (in MB)
        minSize = 0
        # Enable/Disable deleting ignored files (samples and invalid media files)
        delete_ignored = 0
        ##### Enable if NzbDrone is on a remote server for this category
        remote_path = 0
        ##### Set to path where download client places completed downloads locally for this category
        watch_dir =
        ##### Set to define import behavior Move or Copy
        importMode = Copy

[Watcher3]
    #### autoProcessing for Movies
    #### movie - category that gets called for post-processing with CPS
    [[movie]]
        enabled = 0
        apikey =
        host = localhost
        port = 9090
        ###### ADVANCED USE - ONLY EDIT IF YOU KNOW WHAT YOU'RE DOING ######
        ssl = 0
        web_root =
        # api key for www.omdbapi.com (used as alternative to imdb)
        omdbapikey =
        # Enable/Disable linking for Torrents
        Torrent_NoLink = 0
        keep_archive = 1
        delete_failed = 0
        wait_for = 0
        extract = 1
        # Set this to minimum required size to consider a media file valid (in MB)
        minSize = 0
        # Enable/Disable deleting ignored files (samples and invalid media files)
        delete_ignored = 0
        ##### Enable if Watcher3 is on a remote server for this category
        remote_path = 0
        ##### Set to path where download client places completed downloads locally for this category
        watch_dir =
        ##### Set the recursive directory permissions to the following (0 to disable)
        chmodDirectory = 0

[SickBeard]
    #### autoProcessing for TV Series
    #### tv - category that gets called for post-processing with SB
    [[tv]]
        enabled = 0
        host = localhost
        port = 8081
        apikey =
        username =
        password =
        ###### ADVANCED USE - ONLY EDIT IF YOU KNOW WHAT YOU'RE DOING ######
        web_root =
        ssl = 0
        fork = auto
        delete_failed = 0
        # Enable/Disable linking for Torrents
        Torrent_NoLink = 0
        keep_archive = 1
        process_method =
        # force processing of already processed content when running a manual scan.
        force = 0
        # Additionally to force, handle the download as a priority downlaod.
        # The processed files will always replace existing qualities, also if this is a lower quality.
        is_priority = 0
        # tell SickRage/Medusa to delete all source files after processing.
        delete_on = 0
        # tell Medusa to ignore check for associated subtitle check when postponing release
        ignore_subs = 0
        extract = 1
        nzbExtractionBy = Downloader
        # Set this to minimum required size to consider a media file valid (in MB)
        minSize = 0
        # Enable/Disable deleting ignored files (samples and invalid media files)
        delete_ignored = 0
        ##### Enable if SickBeard is on a remote server for this category
        remote_path = 0
        ##### Set to path where download client places completed downloads locally for this category
        watch_dir =
        ##### Set the recursive directory permissions to the following (0 to disable)
        chmodDirectory = 0
        ##### pyMedusa (fork=medusa-apiv2) uses async postprocessing. Wait a maximum of x minutes for a pp result
        wait_for = 10

[SiCKRAGE]
    #### autoProcessing for TV Series
    #### tv - category that gets called for post-processing with SR
    [[tv]]
        enabled = 0
        host = localhost
        port = 8081
        apikey =
        # api version 1 uses api keys
        # api version 2 uses SSO user/pass
        api_version = 2
        # SSO login requires API v2 to be set
        sso_username =
        sso_password =
        ###### ADVANCED USE - ONLY EDIT IF YOU KNOW WHAT YOU'RE DOING ######
        web_root =
        ssl = 0
        delete_failed = 0
        # Enable/Disable linking for Torrents
        Torrent_NoLink = 0
        keep_archive = 1
        process_method =
        # force processing of already processed content when running a manual scan.
        force = 0
        # tell SickRage/Medusa to delete all source files after processing.
        delete_on = 0
        # tell Medusa to ignore check for associated subtitle check when postponing release
        ignore_subs = 0
        extract = 1
        nzbExtractionBy = Downloader
        # Set this to minimum required size to consider a media file valid (in MB)
        minSize = 0
        # Enable/Disable deleting ignored files (samples and invalid media files)
        delete_ignored = 0
        ##### Enable if SickBeard is on a remote server for this category
        remote_path = 0
        ##### Set to path where download client places completed downloads locally for this category
        watch_dir =
        ##### Set the recursive directory permissions to the following (0 to disable)
        chmodDirectory = 0

[NzbDrone]
    #### Formerly known as NzbDrone this is now Sonarr
    #### autoProcessing for TV Series
    #### ndCategory - category that gets called for post-processing with NzbDrone/Sonarr
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
        # Enable/Disable linking for Torrents
        Torrent_NoLink = 0
        keep_archive = 1
        extract = 1
        nzbExtractionBy = Downloader
        wait_for = 6
        # Set this to minimum required size to consider a media file valid (in MB)
        minSize = 0
        # Enable/Disable deleting ignored files (samples and invalid media files)
        delete_ignored = 0
        ##### Enable if NzbDrone is on a remote server for this category
        remote_path = 0
        ##### Set to path where download client places completed downloads locally for this category
        watch_dir =
        ##### Set to define import behavior Move or Copy
        importMode = Copy

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
        delete_failed = 0
        wait_for = 2
        # Enable/Disable linking for Torrents
        Torrent_NoLink = 0
        keep_archive = 1
        extract = 1
        # Set this to minimum required size to consider a media file valid (in MB)
        minSize = 0
        # Enable/Disable deleting ignored files (samples and invalid media files)
        delete_ignored = 0
        ##### Enable if HeadPhones is on a remote server for this category
        remote_path = 0
        ##### Set to path where download client places completed downloads locally for this category
        watch_dir =

[Lidarr]
    #### autoProcessing for Music
    #### LiCategory - category that gets called for post-processing with Lidarr
    [[music]]
        enabled = 0
        apikey =
        host = localhost
        port = 8686
        ###### ADVANCED USE - ONLY EDIT IF YOU KNOW WHAT YOU'RE DOING ######
        web_root =
        ssl = 0
        delete_failed = 0
        # Enable/Disable linking for Torrents
        Torrent_NoLink = 0
        keep_archive = 1
        extract = 1
        nzbExtractionBy = Downloader
        wait_for = 6
        # Set this to minimum required size to consider a media file valid (in MB)
        minSize = 0
        # Enable/Disable deleting ignored files (samples and invalid media files)
        delete_ignored = 0
        ##### Enable if NzbDrone is on a remote server for this category
        remote_path = 0
        ##### Set to path where download client places completed downloads locally for this category
        watch_dir =

[Mylar]
    #### autoProcessing for Comics
    #### comics - category that gets called for post-processing with Mylar
    [[comics]]
        enabled = 0
        host = localhost
        port= 8090
        apikey=
        ###### ADVANCED USE - ONLY EDIT IF YOU KNOW WHAT YOU'RE DOING ######
        web_root=
        ssl=0
        # Enable/Disable linking for Torrents
        Torrent_NoLink = 0
        keep_archive = 1
        extract = 1
        # Set this to minimum required size to consider a media file valid (in MB)
        minSize = 0
        # Enable/Disable deleting ignored files (samples and invalid media files)
        delete_ignored = 0
        ##### Enable if Mylar is on a remote server for this category
        remote_path = 0
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
        ######
        library = Set to path where you want the processed games to be moved to.
        ###### ADVANCED USE - ONLY EDIT IF YOU KNOW WHAT YOU'RE DOING ######
        ssl = 0
        web_root =
        # Enable/Disable linking for Torrents
        Torrent_NoLink = 0
        keep_archive = 1
        extract = 1
        # Set this to minimum required size to consider a media file valid (in MB)
        minSize = 0
        # Enable/Disable deleting ignored files (samples and invalid media files)
        delete_ignored = 0
        ##### Enable if Gamez is on a remote server for this category
        remote_path = 0
        ##### Set to path where download client places completed downloads locally for this category
        watch_dir =

[LazyLibrarian]
    #### autoProcessing for LazyLibrarian
    #### books - category that gets called for post-processing with LazyLibrarian
    [[books]]
        enabled = 0
        apikey =
        host = localhost
        port = 5299
        ###### ADVANCED USE - ONLY EDIT IF YOU KNOW WHAT YOU'RE DOING ######
        ssl = 0
        web_root =
        # Enable/Disable linking for Torrents
        Torrent_NoLink = 0
        keep_archive = 1
        extract = 1
        # Set this to minimum required size to consider a media file valid (in MB)
        minSize = 0
        # Enable/Disable deleting ignored files (samples and invalid media files)
        delete_ignored = 0
        ##### Enable if LazyLibrarian is on a remote server for this category
        remote_path = 0
        ##### Set to path where download client places completed downloads locally for this category
        watch_dir =


[Network]
    # Enter Mount points as LocalPath,RemotePath and separate each pair with '|'
    # e.g. MountPoints = /volume1/Public/,E:\|/volume2/share/,\\NAS\
    mount_points =

[Nzb]
    ###### clientAgent - Supported clients: sabnzbd, nzbget
    clientAgent = sabnzbd
    ###### SabNZBD (You must edit this if you're using nzbToMedia.py with SabNZBD)
    sabnzbd_host = http://localhost
    sabnzbd_port = 8080
    sabnzbd_apikey =
    ###### Enter the default path to your default download directory (non-category downloads). this directory is protected by safe_mode.
    default_downloadDirectory =
    # enable this option to prevent nzbToMedia from running in manual mode and scanning an entire directory.
    no_manual = 0

[Torrent]
    ###### clientAgent - Supported clients: utorrent, transmission, deluge, rtorrent, vuze, qbittorrent, synods, other
    clientAgent = other
    ###### useLink - Set to hard for physical links, sym for symbolic links, move to move, move-sym to move and link back, and no to not use links (copy)
    useLink = hard
    ###### outputDirectory - Default output directory (categories will be appended as sub directory to outputDirectory)
    outputDirectory = /abs/path/to/complete/
    ###### Enter the default path to your default download directory (non-category downloads). this directory is protected by safe_mode.
    default_downloadDirectory =
    ###### Other categories/labels defined for your downloader. Does not include CouchPotato, SickBeard, HeadPhones, Mylar categories.
    categories = music_videos,pictures,software,manual
    ###### A list of categories that you don't want to be flattened (i.e preserve the directory structure when copying/linking.
    noFlatten = pictures,manual
    ###### uTorrent Hardlink solution (You must edit this if you're using TorrentToMedia.py with uTorrent)
    uTorrentWEBui = http://localhost:8090/gui/
    uTorrentUSR = your username
    uTorrentPWD = your password
    ###### Transmission (You must edit this if you're using TorrentToMedia.py with Transmission)
    TransmissionHost = localhost
    TransmissionPort = 9091
    TransmissionUSR = your username
    TransmissionPWD = your password
    #### Deluge (You must edit this if you're using TorrentToMedia.py with deluge. Note that the host/port is for the deluge daemon, not the webui)
    DelugeHost = localhost
    DelugePort = 58846
    DelugeUSR = your username
    DelugePWD = your password
    ###### qBittorrent (You must edit this if you're using TorrentToMedia.py with qBittorrent)
    qBittorrentHost = localhost
    qBittorrentPort = 8080
    qBittorrentUSR = your username
    qBittorrentPWD = your password
    ###### Synology Download Station (You must edit this if you're using TorrentToMedia.py with Synology DS)
    synoHost = localhost
    synoPort = 5000
    synoUSR = your username
    synoPWD = your password
    ###### ADVANCED USE - ONLY EDIT IF YOU KNOW WHAT YOU'RE DOING ######
    deleteOriginal = 0
    chmodDirectory = 0
    resume = 1
    resumeOnFailure = 1
    # enable this option to prevent TorrentToMedia from running in manual mode and scanning an entire directory.
    no_manual = 0

[Extensions]
    compressedExtensions = .zip,.rar,.7z,.gz,.bz,.tar,.arj,.1,.01,.001
    mediaExtensions = .mkv,.avi,.divx,.xvid,.mov,.wmv,.mp4,.mpg,.mpeg,.vob,.iso,.m4v,.ts
    audioExtensions = .mp3, .aac, .ogg, .ape, .m4a, .asf, .wma, .flac
    metaExtensions = .nfo,.sub,.srt,.jpg,.gif

[Plex]
    # Only enter these details if you want to update plex library after processing.
    # Do not enter these details if you send the plex notifications from Sickbeard/CouchPotato.
    plex_host = localhost
    plex_port = 32400
    plex_token =
    plex_ssl = 0
    # Enter Plex category to section mapping as Category,section and separate each pair with '|'
    # e.g. plex_sections = movie,3|tv,4
    plex_sections =

[Transcoder]
    # getsubs. enable to download subtitles.
    getSubs = 0
    # subLanguages. create a list of languages in the order you want them in your subtitles.
    subLanguages = eng,spa,fra
    # transcode. enable to use transcoder
    transcode = 0
    ###### duplicate =1 will create a new file. =0 will replace the original
    duplicate = 1
    # concat. joins cd1 cd2 etc into a single video.
    concat = 1
    # IgnoreExtensions is a comma-separated list of extensions that will not be transcoded.
    ignoreExtensions = .avi,.mkv,.mp4
    # outputFastStart. 1 will use -movflags + faststart. 0 will disable this from being used.
    outputFastStart = 0
    # outputQualityPercent. used as -q:a value. 0 will disable this from being used.
    outputQualityPercent = 0
    # outputVideoPath. Set path you want transcoded videos moved to. Leave blank to disable.
    outputVideoPath =
    # processOutput. 1 will send the outputVideoPath to SickBeard/CouchPotato. 0 will send original files.
    processOutput = 0
    # audioLanguage. set the 3 letter language code you want as your primary audio track.
    audioLanguage = eng
    # allAudioLanguages. 1 will keep all audio tracks (uses AudioCodec3) where available.
    allAudioLanguages = 0
    # allSubLanguages. 1 will keep all existing sub languages. 0 will discard those not in your list above.
    allSubLanguages = 0
    # embedSubs. 1 will embed external sub/srt subs into your video if this is supported.
    embedSubs = 1
    # burnInSubtitle. burns the default sub language into your video (needed for players that don't support subs)
    burnInSubtitle = 0
    # extractSubs. 1 will extract subs from the video file and save these as external srt files.
    extractSubs = 0
    # externalSubDir. set the directory where subs should be saved (if not the same directory as the video)
    externalSubDir =
    # hwAccel. 1 will set ffmpeg to enable hardware acceleration (this requires a recent ffmpeg)
    hwAccel = 0
    # generalOptions. Enter your additional ffmpeg options (these insert before the '-i' input files) here with commas to separate each option/value (i.e replace spaces with commas).
    generalOptions =
    # otherOptions. Enter your additional ffmpeg options (these insert after the '-i' input files and before the output file) here with commas to separate each option/value (i.e replace spaces with commas).
    otherOptions =
    # outputDefault. Loads default configs for the selected device. The remaining options below are ignored.
    # If you want to use your own profile, leave this blank and set the remaining options below.
    # outputDefault profiles allowed: iPad, iPad-1080p, iPad-720p, Apple-TV2, iPod, iPhone, PS3, xbox, Roku-1080p, Roku-720p, Roku-480p, mkv, mkv-bluray, mp4-scene-release
    outputDefault =
    #### Define custom settings below.
    outputVideoExtension = .mp4
    outputVideoCodec = libx264
    VideoCodecAllow =
    outputVideoPreset = medium
    outputVideoResolution = 1920:1080
    outputVideoFramerate = 24
    outputVideoBitrate = 800000
    outputVideoCRF = 19
    outputVideoLevel = 3.1
    outputAudioCodec = ac3
    AudioCodecAllow =
    outputAudioChannels = 6
    outputAudioBitrate = 640k
    outputAudioTrack2Codec = libfaac
    AudioCodec2Allow =
    outputAudioTrack2Channels = 2
    outputAudioTrack2Bitrate = 128000
    outputAudioOtherCodec = libmp3lame
    AudioOtherCodecAllow =
    outputAudioOtherChannels =
    outputAudioOtherBitrate = 128000
    outputSubtitleCodec =

[WakeOnLan]
    ###### set wake = 1 to send WOL broadcast to the mac and test the server (e.g. xbmc) the host and port specified.
    wake = 0
    host = 192.168.1.37
    port = 80
    mac = 00:01:2e:2D:64:e1

[UserScript]
    #Use user_script for uncategorized downloads
    #Set the categories to use external script.
    #Use "UNCAT" to process non-category downloads, and "ALL" for all defined categories.
    [[UNCAT]]
        #Enable/Disable this subsection category
        enabled = 0
        Torrent_NoLink = 0
        keep_archive = 1
        extract = 1
        #Enable if you are sending commands to a remote server for this category
        remote_path = 0
        #What extension do you want to process? Specify all the extension, or use "ALL" to process all files.
        user_script_mediaExtensions = .mkv,.avi,.divx,.xvid,.mov,.wmv,.mp4,.mpg,.mpeg
        #Specify the path to your custom script. Use "None" if you wish to link this category, but NOT run any external script.
        user_script_path = /nzbToMedia/userscripts/script.sh
        #Specify the argument(s) passed to script, comma separated in order.
        #for example FP,FN,DN, TN, TL for file path (absolute file name with path), file name, absolute directory name (with path), Torrent Name, Torrent Label/Category.
        #So the result is /media/test/script/script.sh FP FN DN TN TL. Add other arguments as needed eg -f, -r
        user_script_param = FN
        #Set user_script_runOnce = 0 to run for each file, or 1 to only run once (presumably on the entire directory).
        user_script_runOnce = 0
        #Specify the successcodes returned by the user script as a comma separated list. Linux default is 0
        user_script_successCodes = 0
        #Clean after? Note that delay function is used to prevent possible mistake :) Delay is intended as seconds
        user_script_clean = 1
        delay = 120
        #Unique path (directory) created for every download. set 0 to disable.
        unique_path = 1
        ##### Set to path where download client places completed downloads locally for this category
        watch_dir =

[ASCII]
    #Set convert =1 if you want to convert any "foreign" characters to ASCII (UTF8) before passing to SB/CP etc. Default is disabled (0).
    convert = 0

[Passwords]
    # enter the full path to a text file containing passwords to be used for extraction attempts.
    # In the passwords file, every password should be on a new line
    PassWordFile =

[Custom]
    # enter a list (comma separated) of Group Tags you want removed from filenames to help with subtitle matching.
    # e.g remove_group = [rarbag],-NZBgeek
    # be careful if your "group" is a common "real" word. Please report if you have any group replacements that would fall in this category.
    remove_group =
