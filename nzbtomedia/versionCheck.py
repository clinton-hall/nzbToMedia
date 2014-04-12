import os
import shutil
import urllib
import tarfile
import stat
import traceback
import gh_api as github
import nzbtomedia
from nzbtomedia import logger

class CheckVersion():
    """
    Version check class meant to run as a thread object with the SB scheduler.
    """

    def __init__(self):
        self.updater = SourceUpdateManager()

    def run(self):
        self.check_for_new_version()

    def check_for_new_version(self, force=False):
        """
        Checks the internet for a newer version.

        returns: bool, True for new version or False for no new version.

        force: if true the VERSION_NOTIFY setting will be ignored and a check will be forced
        """

        logger.info("Checking if nzbToMedia needs an update")
        if not self.updater.need_update():
            NEWEST_VERSION_STRING = None
            logger.info("No update needed")

            if force:
                logger.info("No update needed")
            return False

        if not self.updater._cur_commit_hash:
            logger.info("Unknown current version number, don't know if we should update or not")
        elif self.updater._num_commits_behind > 0:
            logger.info("There is a newer version available, (you're " + str(self.updater._num_commits_behind) + " commit(s) behind")

        return True

    def update(self):
        if self.updater.need_update():
            return self.updater.update()

class UpdateManager():
    def get_github_repo_user(self):
        return 'clinton-hall'

    def get_github_repo(self):
        return 'nzbToMedia'

#    def get_update_url(self):
#        return nzbtomedia.WEB_ROOT + "/home/update/?pid=" + str(nzbtomedia.PID)

class SourceUpdateManager(UpdateManager):
    
    def __init__(self):
        self.github_repo_user = self.get_github_repo_user()
        self.github_repo = self.get_github_repo()
        self.branch = 'master'

        self._cur_commit_hash = None
        self._newest_commit_hash = None
        self._num_commits_behind = 0

    def _find_installed_version(self):

        version_file = os.path.join(nzbtomedia.PROGRAM_DIR, u'version.txt')

        if not os.path.isfile(version_file):
            self._cur_commit_hash = None
            return

        try:
            with open(version_file, 'r') as fp:
                self._cur_commit_hash = fp.read().strip(' \n\r')
        except EnvironmentError, e:
            logger.debug("Unable to open 'version.txt': " + str(e))

        if not self._cur_commit_hash:
            self._cur_commit_hash = None

    def need_update(self):

        self._find_installed_version()

        try:
            self._check_github_for_update()
        except Exception, e:
            logger.error("Unable to contact github, can't check for update: " + repr(e))
            return False

        if not self._cur_commit_hash or self._num_commits_behind > 0:
            return True

        return False

    def _check_github_for_update(self):
        """
        Uses pygithub to ask github if there is a newer version that the provided
        commit hash. If there is a newer version it sets Sick Beard's version text.

        commit_hash: hash that we're checking against
        """

        self._num_commits_behind = 0
        self._newest_commit_hash = None

        gh = github.GitHub(self.github_repo_user, self.github_repo, self.branch)

        # try to get newest commit hash and commits behind directly by comparing branch and current commit
        if self._cur_commit_hash:
            branch_compared = gh.compare(base=self.branch, head=self._cur_commit_hash)

            if 'base_commit' in branch_compared:
                self._newest_commit_hash = branch_compared['base_commit']['sha']

            if 'behind_by' in branch_compared:
                self._num_commits_behind = int(branch_compared['behind_by'])

        # fall back and iterate over last 100 (items per page in gh_api) commits
        if not self._newest_commit_hash:

            for curCommit in gh.commits():
                if not self._newest_commit_hash:
                    self._newest_commit_hash = curCommit['sha']
                    if not self._cur_commit_hash:
                        break

                if curCommit['sha'] == self._cur_commit_hash:
                    break

                # when _cur_commit_hash doesn't match anything _num_commits_behind == 100
                self._num_commits_behind += 1

        logger.debug("cur_commit = " + str(self._cur_commit_hash) + ", newest_commit = " + str(self._newest_commit_hash)
                   + ", num_commits_behind = " + str(self._num_commits_behind))

    def set_newest_text(self):

        # if we're up to date then don't set this
        nzbtomedia.NEWEST_VERSION_STRING = None

        if not self._cur_commit_hash:
            logger.info("Unknown current version number, don't know if we should update or not")
        elif self._num_commits_behind > 0:
            logger.info("There is a newer version available, (you're " + str(self._num_commits_behind) + " commit(s) behind")

    def update(self):
        """
        Downloads the latest source tarball from github and installs it over the existing version.
        """
        base_url = 'https://github.com/' + self.github_repo_user + '/' + self.github_repo
        tar_download_url = base_url + '/tarball/' + self.branch
        version_path = os.path.join(nzbtomedia.PROGRAM_DIR, u'version.txt')

        try:
            # prepare the update dir
            sb_update_dir = os.path.join(nzbtomedia.PROGRAM_DIR, u'sb-update')

            if os.path.isdir(sb_update_dir):
                logger.info("Clearing out update folder " + sb_update_dir + " before extracting")
                shutil.rmtree(sb_update_dir)

            logger.info("Creating update folder " + sb_update_dir + " before extracting")
            os.makedirs(sb_update_dir)

            # retrieve file
            logger.info("Downloading update from " + repr(tar_download_url))
            tar_download_path = os.path.join(sb_update_dir, u'sb-update.tar')
            urllib.urlretrieve(tar_download_url, tar_download_path)

            if not str(os.path.isfile, tar_download_path):
                logger.error("Unable to retrieve new version from " + tar_download_url + ", can't update")
                return False

            if not str(tarfile.is_tarfile, tar_download_path):
                logger.error("Retrieved version from " + tar_download_url + " is corrupt, can't update")
                return False

            # extract to sb-update dir
            logger.info("Extracting file " + tar_download_path)
            tar = tarfile.open(tar_download_path)
            tar.extractall(sb_update_dir)
            tar.close()

            # delete .tar.gz
            logger.info("Deleting file " + tar_download_path)
            os.remove(tar_download_path)

            # find update dir name
            update_dir_contents = [x for x in os.listdir(sb_update_dir) if
                                   os.path.isdir(os.path.join(sb_update_dir, x))]
            if len(update_dir_contents) != 1:
                logger.error("Invalid update data, update failed: " + str(update_dir_contents))
                return False
            content_dir = os.path.join(sb_update_dir, update_dir_contents[0])

            # walk temp folder and move files to main folder
            logger.info("Moving files from " + content_dir + " to " + nzbtomedia.PROGRAM_DIR)
            for dirname, dirnames, filenames in os.walk(content_dir):  # @UnusedVariable
                dirname = dirname[len(content_dir) + 1:]
                for curfile in filenames:
                    old_path = os.path.join(content_dir, dirname, curfile)
                    new_path = os.path.join(nzbtomedia.PROGRAM_DIR, dirname, curfile)

                    #Avoid DLL access problem on WIN32/64
                    #These files needing to be updated manually
                    #or find a way to kill the access from memory
                    if curfile in ('unrar.dll', 'unrar64.dll'):
                        try:
                            os.chmod(new_path, stat.S_IWRITE)
                            os.remove(new_path)
                            os.renames(old_path, new_path)
                        except Exception, e:
                            logger.debug("Unable to update " + new_path + ': ' + str(e))
                            os.remove(old_path)  # Trash the updated file without moving in new path
                        continue

                    if os.path.isfile(new_path):
                        os.remove(new_path)
                    os.renames(old_path, new_path)

            # update version.txt with commit hash
            try:
                with open(version_path, 'w') as ver_file:
                    ver_file.write(self._newest_commit_hash)
            except EnvironmentError, e:
                logger.error("Unable to write version file, update not complete: " + str(e))
                return False

        except Exception, e:
            logger.error("Error while trying to update: " + str(e))
            logger.debug("Traceback: " + traceback.format_exc())
            return False

        return True