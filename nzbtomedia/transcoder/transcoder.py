import errno
import os
import platform
import urllib2
import traceback
import nzbtomedia
from subprocess import call
from nzbtomedia import logger

def isVideoGood(videofile):
    fileNameExt = os.path.basename(videofile)
    fileName, fileExt = os.path.splitext(fileNameExt)
    if fileExt not in nzbtomedia.MEDIACONTAINER:
        return True

    if platform.system() == 'Windows':
        bitbucket = open('NUL')
    else:
        bitbucket = open('/dev/null')

    if not nzbtomedia.FFPROBE:
        logger.error("Cannot detect corrupt video files!, set your ffmpeg_path in your autoProcessMedia.cfg ...", 'TRANSCODER')
        return False

    command = [nzbtomedia.FFPROBE, videofile]
    try:
        logger.info('Checking [%s] for corruption, please stand by ...' % (fileNameExt), 'TRANSCODER')
        result = call(command, stdout=bitbucket, stderr=bitbucket)
    except:
        logger.error("Checking [%s] for corruption has failed" % (fileNameExt), 'TRANSCODER')
        return False

    if result == 0:
        logger.info("SUCCESS: [%s] has no corruption." % (fileNameExt), 'TRANSCODER')
        return True
    else:
        logger.error("FAILED: [%s] is corrupted!" % (fileNameExt), 'TRANSCODER')
        return False

def Transcode_directory(dirName):
    if platform.system() == 'Windows':
        bitbucket = open('NUL')
    else:
        bitbucket = open('/dev/null')

    if not nzbtomedia.FFMPEG:
        logger.error("Cannot transcode files!, set your ffmpeg_path in your autoProcessMedia.cfg ...")
        return 1

    logger.info("Checking for files to be transcoded")
    final_result = 0 # initialize as successful
    for file in nzbtomedia.listMediaFiles(dirName):
        name, ext = os.path.splitext(file)
        if ext in [i.replace(".","") for i in nzbtomedia.MEDIACONTAINER]:
            continue
        if ext == nzbtomedia.OUTPUTVIDEOEXTENSION: # we need to change the name to prevent overwriting itself.
            nzbtomedia.OUTPUTVIDEOEXTENSION = '-transcoded' + nzbtomedia.OUTPUTVIDEOEXTENSION # adds '-transcoded.ext'

        newfilePath = os.path.normpath(name + nzbtomedia.OUTPUTVIDEOEXTENSION)

        command = [nzbtomedia.FFMPEG, '-loglevel', 'warning', '-i', file, '-map', '0'] # -map 0 takes all input streams
        if platform.system() != 'Windows':
            command = ['nice', '-%d' % nzbtomedia.NICENESS] + command

        if len(nzbtomedia.OUTPUTVIDEOCODEC) > 0:
            command.append('-c:v')
            command.append(nzbtomedia.OUTPUTVIDEOCODEC)
            if nzbtomedia.OUTPUTVIDEOCODEC == 'libx264' and nzbtomedia.OUTPUTVIDEOPRESET:
                command.append('-pre')
                command.append(nzbtomedia.OUTPUTVIDEOPRESET)
        else:
            command.append('-c:v')
            command.append('copy')
        if len(nzbtomedia.OUTPUTVIDEOFRAMERATE) > 0:
            command.append('-r')
            command.append(str(nzbtomedia.OUTPUTVIDEOFRAMERATE))
        if len(nzbtomedia.OUTPUTVIDEOBITRATE) > 0:
            command.append('-b:v')
            command.append(str(nzbtomedia.OUTPUTVIDEOBITRATE))
        if len(nzbtomedia.OUTPUTAUDIOCODEC) > 0:
            command.append('-c:a')
            command.append(nzbtomedia.OUTPUTAUDIOCODEC)
            if nzbtomedia.OUTPUTAUDIOCODEC == 'aac': # Allow users to use the experimental AAC codec that's built into recent versions of ffmpeg
                command.append('-strict')
                command.append('-2')
        else:
            command.append('-c:a')
            command.append('copy')
        if len(nzbtomedia.OUTPUTAUDIOBITRATE) > 0:
            command.append('-b:a')
            command.append(str(nzbtomedia.OUTPUTAUDIOBITRATE))
        if nzbtomedia.OUTPUTFASTSTART > 0:
            command.append('-movflags')
            command.append('+faststart')
        if nzbtomedia.OUTPUTQUALITYPERCENT > 0:
            command.append('-q:a')
            command.append(str(nzbtomedia.OUTPUTQUALITYPERCENT))
        if len(nzbtomedia.OUTPUTSUBTITLECODEC) > 0: # Not every subtitle codec can be used for every video container format!
            command.append('-c:s')
            command.append(nzbtomedia.OUTPUTSUBTITLECODEC) # http://en.wikibooks.org/wiki/FFMPEG_An_Intermediate_Guide/subtitle_options
        else:
            command.append('-sn')  # Don't copy the subtitles over
        command.append(newfilePath)

        try: # Try to remove the file that we're transcoding to just in case. (ffmpeg will return an error if it already exists for some reason)
            os.remove(newfilePath)
        except OSError, e:
            if e.errno != errno.ENOENT: # Ignore the error if it's just telling us that the file doesn't exist
                logger.debug("Error when removing transcoding target: %s" % (e))
        except Exception, e:
            logger.debug("Error when removing transcoding target: %s" % (e))

        logger.info("Transcoding video: %s" % (file))
        cmd = ""
        for item in command:
            cmd = cmd + " " + item
        logger.debug("calling command:%s" % (cmd))
        result = 1 # set result to failed in case call fails.
        try:
            result = call(command, stdout=bitbucket, stderr=bitbucket)
        except:
            logger.error("Transcoding of video %s has failed" % (file))

        if result == 0:
            logger.info("Transcoding of video %s to %s succeeded" % (file, newfilePath))
            if nzbtomedia.DUPLICATE == 0: # we get rid of the original file
                os.unlink(file)
        else:
            logger.error("Transcoding of video %s to %s failed" % (file, newfilePath))
        # this will be 0 (successful) it all are successful, else will return a positive integer for failure.
        final_result = final_result + result
    return final_result

def install_ffmpeg():
    # goto script folder
    os.chdir(os.path.join(os.getcwd(), os.path.dirname(__file__)))

    # path relative to this script file
    # where will the dependency packages be downloaded
    DOWNLOAD_DIR = "download"

    def my_mkdir(path):
        if os.path.exists(path) == False:
            os.makedirs(path)

    def my_remove(path):
        if os.path.exists(path):
            os.remove(path)

    def my_exec(cmd):
        print "[cmd] %s" % cmd
        os.system(cmd)

    def prepare_package(pkg_url):
        ret = True
        my_mkdir(DOWNLOAD_DIR)
        pkg_name = os.path.basename(urllib2.urlparse.urlparse(pkg_url).path)
        pkg_fpath = os.path.join(DOWNLOAD_DIR, pkg_name)
        tmp_fpath = os.path.join(DOWNLOAD_DIR, pkg_name + ".downloading")
        my_remove(tmp_fpath)
        if os.path.exists(pkg_fpath):
            print "%s already downloaded" % pkg_name
        else:
            f = open(tmp_fpath, "wb")
            try:
                print "downloading %s from %s" % (pkg_name, pkg_url)
                f.write(urllib2.urlopen(pkg_url).read())
                os.rename(tmp_fpath, pkg_fpath)
            except:
                traceback.print_exc()
                my_remove(tmp_fpath)
                exit(1)
            finally:
                f.close()
        if ret == True:
            if pkg_name.endswith(".tar.bz2"):
                if os.path.exists(os.path.join(DOWNLOAD_DIR, pkg_name[:-8])) == False:
                    print "extracting %s" % pkg_name
                    my_exec("cd '%s' ; tar xjf %s" % (DOWNLOAD_DIR, pkg_name))
            if pkg_name.endswith(".tar.gz"):
                if os.path.exists(os.path.join(DOWNLOAD_DIR, pkg_name[:-7])) == False:
                    print "extracting %s" % pkg_name
                    my_exec("cd '%s' ; tar xzf %s" % (DOWNLOAD_DIR, pkg_name))
        return ret

    # build yasm
    prepare_package("http://www.tortall.net/projects/yasm/releases/yasm-1.2.0.tar.gz")
    my_exec("""
        cd %s/yasm-1.2.0
        ./configure
        make
        make install
    """ % (DOWNLOAD_DIR))


    # build x264
    prepare_package("ftp://ftp.videolan.org/pub/x264/snapshots/last_stable_x264.tar.bz2")
    my_exec("""
        cd %s/last_stable_x264
        ./configure --enable-static'
        make
        make install
    """ % (DOWNLOAD_DIR))

    # build ffmpeg
    prepare_package("http://ffmpeg.org/releases/ffmpeg-2.2.1.tar.bz2")
    my_exec("""
        cd %s/ffmpeg-2.2.1
        ./configure \
            --enable-gpl --enable-nonfree \
            --disable-ffserver \
            --disable-shared --enable-static \
            --extra-cflags='-static' \
            --enable-libx264 --enable-pthreads
        make
        make install
    """ % (DOWNLOAD_DIR))

    return True