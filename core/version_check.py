# coding=utf-8
# Author: Nic Wolfe <nic@wolfeden.ca>
# Modified by: echel0n

from __future__ import (
    absolute_import,
    division,
    print_function,
    unicode_literals,
)

import os
import platform
import re
import shutil
import stat
import subprocess
import tarfile
import traceback

from six.moves.urllib.request import urlretrieve

import cleanup
import core
from core import github_api as github, logger


class CheckVersion(object):
    """Version checker that runs in a thread with the SB scheduler."""

    def __init__(self):
        self.install_type = self.find_install_type()
        self.installed_version = None
        self.installed_branch = None

        if self.install_type == 'git':
            self.updater = GitUpdateManager()
        elif self.install_type == 'source':
            self.updater = SourceUpdateManager()
        else:
            self.updater = None

    def run(self):
        self.check_for_new_version()

    def find_install_type(self):
        """
        Determine how this copy of SB was installed.

        returns: type of installation. Possible values are:
            'win': any compiled windows build
            'git': running from source using git
            'source': running from source without git
        """
        # check if we're a windows build
        if os.path.exists(os.path.join(core.APP_ROOT, u'.git')):
            install_type = 'git'
        else:
            install_type = 'source'

        return install_type

    def check_for_new_version(self, force=False):
        """
        Check the internet for a newer version.

        returns: bool, True for new version or False for no new version.

        force: if true the VERSION_NOTIFY setting will be ignored and a check will be forced
        """
        if not core.VERSION_NOTIFY and not force:
            logger.log(u'Version checking is disabled, not checking for the newest version')
            return False

        logger.log(u'Checking if {install} needs an update'.format(install=self.install_type))
        if not self.updater.need_update():
            core.NEWEST_VERSION_STRING = None
            logger.log(u'No update needed')
            return False

        self.updater.set_newest_text()
        return True

    def update(self):
        if self.updater.need_update():
            result = self.updater.update()
            cleanup.clean(cleanup.FOLDER_STRUCTURE)
            return result


class UpdateManager(object):
    def get_github_repo_user(self):
        return core.GIT_USER

    def get_github_repo(self):
        return core.GIT_REPO

    def get_github_branch(self):
        return core.GIT_BRANCH


class GitUpdateManager(UpdateManager):
    def __init__(self):
        self._git_path = self._find_working_git()
        self.github_repo_user = self.get_github_repo_user()
        self.github_repo = self.get_github_repo()
        self.branch = self._find_git_branch()

        self._cur_commit_hash = None
        self._newest_commit_hash = None
        self._num_commits_behind = 0
        self._num_commits_ahead = 0

    def _git_error(self):
        logger.debug(
            'Unable to find your git executable - Set git_path in your autoProcessMedia.cfg OR delete your .git folder and run from source to enable updates.')

    def _find_working_git(self):
        test_cmd = 'version'

        if core.GIT_PATH:
            main_git = '"{git}"'.format(git=core.GIT_PATH)
        else:
            main_git = 'git'

        logger.log(u'Checking if we can use git commands: {git} {cmd}'.format
                   (git=main_git, cmd=test_cmd), logger.DEBUG)
        output, err, exit_status = self._run_git(main_git, test_cmd)

        if exit_status == 0:
            logger.log(u'Using: {git}'.format(git=main_git), logger.DEBUG)
            return main_git
        else:
            logger.log(u'Not using: {git}'.format(git=main_git), logger.DEBUG)

        # trying alternatives

        alternative_git = []

        # osx people who start SB from launchd have a broken path, so try a hail-mary attempt for them
        if platform.system().lower() == 'darwin':
            alternative_git.append('/usr/local/git/bin/git')

        if platform.system().lower() == 'windows':
            if main_git != main_git.lower():
                alternative_git.append(main_git.lower())

        if alternative_git:
            logger.log(u'Trying known alternative git locations', logger.DEBUG)

            for cur_git in alternative_git:
                logger.log(u'Checking if we can use git commands: {git} {cmd}'.format
                           (git=cur_git, cmd=test_cmd), logger.DEBUG)
                output, err, exit_status = self._run_git(cur_git, test_cmd)

                if exit_status == 0:
                    logger.log(u'Using: {git}'.format(git=cur_git), logger.DEBUG)
                    return cur_git
                else:
                    logger.log(u'Not using: {git}'.format(git=cur_git), logger.DEBUG)

        # Still haven't found a working git
        logger.debug('Unable to find your git executable - '
                     'Set git_path in your autoProcessMedia.cfg OR '
                     'delete your .git folder and run from source to enable updates.')

        return None

    def _run_git(self, git_path, args):

        output = None
        err = None

        if not git_path:
            logger.log(u'No git specified, can\'t use git commands', logger.DEBUG)
            exit_status = 1
            return output, err, exit_status

        cmd = '{git} {args}'.format(git=git_path, args=args)

        try:
            logger.log(u'Executing {cmd} with your shell in {directory}'.format
                       (cmd=cmd, directory=core.APP_ROOT), logger.DEBUG)
            p = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                 shell=True, cwd=core.APP_ROOT)
            output, err = p.communicate()
            exit_status = p.returncode

            output = output.decode('utf-8')

            if output:
                output = output.strip()
            if core.LOG_GIT:
                logger.log(u'git output: {output}'.format(output=output), logger.DEBUG)

        except OSError:
            logger.log(u'Command {cmd} didn\'t work'.format(cmd=cmd))
            exit_status = 1

        exit_status = 128 if ('fatal:' in output) or err else exit_status
        if exit_status == 0:
            logger.log(u'{cmd} : returned successful'.format(cmd=cmd), logger.DEBUG)
            exit_status = 0
        elif core.LOG_GIT and exit_status in (1, 128):
            logger.log(u'{cmd} returned : {output}'.format
                       (cmd=cmd, output=output), logger.DEBUG)
        else:
            if core.LOG_GIT:
                logger.log(u'{cmd} returned : {output}, treat as error for now'.format
                           (cmd=cmd, output=output), logger.DEBUG)
            exit_status = 1

        return output, err, exit_status

    def _find_installed_version(self):
        """
        Attempt to find the currently installed version of Sick Beard.

        Uses git show to get commit version.

        Returns: True for success or False for failure
        """
        output, err, exit_status = self._run_git(self._git_path, 'rev-parse HEAD')  # @UnusedVariable

        if exit_status == 0 and output:
            cur_commit_hash = output.strip()
            if not re.match('^[a-z0-9]+$', cur_commit_hash):
                logger.log(u'Output doesn\'t look like a hash, not using it', logger.ERROR)
                return False
            self._cur_commit_hash = cur_commit_hash
            if self._cur_commit_hash:
                core.NZBTOMEDIA_VERSION = self._cur_commit_hash
            return True
        else:
            return False

    def _find_git_branch(self):
        core.NZBTOMEDIA_BRANCH = self.get_github_branch()
        branch_info, err, exit_status = self._run_git(self._git_path, 'symbolic-ref -q HEAD')  # @UnusedVariable
        if exit_status == 0 and branch_info:
            branch = branch_info.strip().replace('refs/heads/', '', 1)
            if branch:
                core.NZBTOMEDIA_BRANCH = branch
                core.GIT_BRANCH = branch
        return core.GIT_BRANCH

    def _check_github_for_update(self):
        """
        Check Github for a new version.

        Uses git commands to check if there is a newer version than
        the provided commit hash. If there is a newer version it
        sets _num_commits_behind.
        """
        self._newest_commit_hash = None
        self._num_commits_behind = 0
        self._num_commits_ahead = 0

        # get all new info from github
        output, err, exit_status = self._run_git(self._git_path, 'fetch origin')

        if not exit_status == 0:
            logger.log(u'Unable to contact github, can\'t check for update', logger.ERROR)
            return

        # get latest commit_hash from remote
        output, err, exit_status = self._run_git(self._git_path, 'rev-parse --verify --quiet \'@{upstream}\'')

        if exit_status == 0 and output:
            cur_commit_hash = output.strip()

            if not re.match('^[a-z0-9]+$', cur_commit_hash):
                logger.log(u'Output doesn\'t look like a hash, not using it', logger.DEBUG)
                return

            else:
                self._newest_commit_hash = cur_commit_hash
        else:
            logger.log(u'git didn\'t return newest commit hash', logger.DEBUG)
            return

        # get number of commits behind and ahead (option --count not supported git < 1.7.2)
        output, err, exit_status = self._run_git(self._git_path, 'rev-list --left-right \'@{upstream}\'...HEAD')

        if exit_status == 0 and output:

            try:
                self._num_commits_behind = int(output.count('<'))
                self._num_commits_ahead = int(output.count('>'))

            except Exception:
                logger.log(u'git didn\'t return numbers for behind and ahead, not using it', logger.DEBUG)
                return

        logger.log(u'cur_commit = {current} % (newest_commit)= {new}, '
                   u'num_commits_behind = {x}, num_commits_ahead = {y}'.format
                   (current=self._cur_commit_hash, new=self._newest_commit_hash,
                    x=self._num_commits_behind, y=self._num_commits_ahead), logger.DEBUG)

    def set_newest_text(self):
        if self._num_commits_ahead:
            logger.log(u'Local branch is ahead of {branch}. Automatic update not possible.'.format
                       (branch=self.branch), logger.ERROR)
        elif self._num_commits_behind:
            logger.log(u'There is a newer version available (you\'re {x} commit{s} behind)'.format
                       (x=self._num_commits_behind, s=u's' if self._num_commits_behind > 1 else u''), logger.MESSAGE)
        else:
            return

    def need_update(self):
        if not self._find_installed_version():
            logger.error('Unable to determine installed version via git, please check your logs!')
            return False

        if not self._cur_commit_hash:
            return True
        else:
            try:
                self._check_github_for_update()
            except Exception as error:
                logger.log(u'Unable to contact github, can\'t check for update: {msg!r}'.format(msg=error), logger.ERROR)
                return False

            if self._num_commits_behind > 0:
                return True

        return False

    def update(self):
        """
        Check git for a new version.

        Calls git pull origin <branch> in order to update Sick Beard.
        Returns a bool depending on the call's success.
        """
        output, err, exit_status = self._run_git(self._git_path, 'pull origin {branch}'.format(branch=self.branch))  # @UnusedVariable

        if exit_status == 0:
            return True

        return False


class SourceUpdateManager(UpdateManager):
    def __init__(self):
        self.github_repo_user = self.get_github_repo_user()
        self.github_repo = self.get_github_repo()
        self.branch = self.get_github_branch()

        self._cur_commit_hash = None
        self._newest_commit_hash = None
        self._num_commits_behind = 0

    def _find_installed_version(self):

        version_file = os.path.join(core.APP_ROOT, u'version.txt')

        if not os.path.isfile(version_file):
            self._cur_commit_hash = None
            return

        try:
            with open(version_file, 'r') as fp:
                self._cur_commit_hash = fp.read().strip(' \n\r')
        except EnvironmentError as error:
            logger.log(u'Unable to open \'version.txt\': {msg}'.format(msg=error), logger.DEBUG)

        if not self._cur_commit_hash:
            self._cur_commit_hash = None
        else:
            core.NZBTOMEDIA_VERSION = self._cur_commit_hash

    def need_update(self):

        self._find_installed_version()

        try:
            self._check_github_for_update()
        except Exception as error:
            logger.log(u'Unable to contact github, can\'t check for update: {msg!r}'.format(msg=error), logger.ERROR)
            return False

        if not self._cur_commit_hash or self._num_commits_behind > 0:
            return True

        return False

    def _check_github_for_update(self):
        """
        Check Github for a new version.

        Uses pygithub to ask github if there is a newer version than
        the provided commit hash. If there is a newer version it sets
        Sick Beard's version text.

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

        logger.log(u'cur_commit = {current} % (newest_commit)= {new}, num_commits_behind = {x}'.format
                   (current=self._cur_commit_hash, new=self._newest_commit_hash, x=self._num_commits_behind), logger.DEBUG)

    def set_newest_text(self):

        # if we're up to date then don't set this
        core.NEWEST_VERSION_STRING = None

        if not self._cur_commit_hash:
            logger.log(u'Unknown current version number, don\'t know if we should update or not', logger.ERROR)
        elif self._num_commits_behind > 0:
            logger.log(u'There is a newer version available (you\'re {x} commit{s} behind)'.format
                       (x=self._num_commits_behind, s=u's' if self._num_commits_behind > 1 else u''), logger.MESSAGE)
        else:
            return

    def update(self):
        """Download and install latest source tarball from github."""
        tar_download_url = 'https://github.com/{org}/{repo}/tarball/{branch}'.format(
            org=self.github_repo_user, repo=self.github_repo, branch=self.branch)
        version_path = os.path.join(core.APP_ROOT, u'version.txt')

        try:
            # prepare the update dir
            sb_update_dir = os.path.join(core.APP_ROOT, u'sb-update')

            if os.path.isdir(sb_update_dir):
                logger.log(u'Clearing out update folder {dir} before extracting'.format(dir=sb_update_dir))
                shutil.rmtree(sb_update_dir)

            logger.log(u'Creating update folder {dir} before extracting'.format(dir=sb_update_dir))
            os.makedirs(sb_update_dir)

            # retrieve file
            logger.log(u'Downloading update from {url!r}'.format(url=tar_download_url))
            tar_download_path = os.path.join(sb_update_dir, u'nzbtomedia-update.tar')
            urlretrieve(tar_download_url, tar_download_path)

            if not os.path.isfile(tar_download_path):
                logger.log(u'Unable to retrieve new version from {url}, can\'t update'.format
                           (url=tar_download_url), logger.ERROR)
                return False

            if not tarfile.is_tarfile(tar_download_path):
                logger.log(u'Retrieved version from {url} is corrupt, can\'t update'.format
                           (url=tar_download_url), logger.ERROR)
                return False

            # extract to sb-update dir
            logger.log(u'Extracting file {path}'.format(path=tar_download_path))
            tar = tarfile.open(tar_download_path)
            tar.extractall(sb_update_dir)
            tar.close()

            # delete .tar.gz
            logger.log(u'Deleting file {path}'.format(path=tar_download_path))
            os.remove(tar_download_path)

            # find update dir name
            update_dir_contents = [x for x in os.listdir(sb_update_dir) if
                                   os.path.isdir(os.path.join(sb_update_dir, x))]
            if len(update_dir_contents) != 1:
                logger.log(u'Invalid update data, update failed: {0}'.format(update_dir_contents), logger.ERROR)
                return False
            content_dir = os.path.join(sb_update_dir, update_dir_contents[0])

            # walk temp folder and move files to main folder
            logger.log(u'Moving files from {source} to {destination}'.format
                       (source=content_dir, destination=core.APP_ROOT))
            for dirname, _, filenames in os.walk(content_dir):  # @UnusedVariable
                dirname = dirname[len(content_dir) + 1:]
                for curfile in filenames:
                    old_path = os.path.join(content_dir, dirname, curfile)
                    new_path = os.path.join(core.APP_ROOT, dirname, curfile)

                    # Avoid DLL access problem on WIN32/64
                    # These files needing to be updated manually
                    # or find a way to kill the access from memory
                    if curfile in ('unrar.dll', 'unrar64.dll'):
                        try:
                            os.chmod(new_path, stat.S_IWRITE)
                            os.remove(new_path)
                            os.renames(old_path, new_path)
                        except Exception as error:
                            logger.log(u'Unable to update {path}: {msg}'.format
                                       (path=new_path, msg=error), logger.DEBUG)
                            os.remove(old_path)  # Trash the updated file without moving in new path
                        continue

                    if os.path.isfile(new_path):
                        os.remove(new_path)
                    os.renames(old_path, new_path)

            # update version.txt with commit hash
            try:
                with open(version_path, 'w') as ver_file:
                    ver_file.write(self._newest_commit_hash)
            except EnvironmentError as error:
                logger.log(u'Unable to write version file, update not complete: {msg}'.format
                           (msg=error), logger.ERROR)
                return False

        except Exception as error:
            logger.log(u'Error while trying to update: {msg}'.format
                       (msg=error), logger.ERROR)
            logger.log(u'Traceback: {error}'.format(error=traceback.format_exc()), logger.DEBUG)
            return False

        return True
