# Author: Nic Wolfe <nic@wolfeden.ca>
# Modified by: echel0n
from __future__ import annotations

import logging
import os
import platform
import re
import shutil
import stat
import subprocess
import tarfile
import traceback
from subprocess import PIPE, STDOUT
from urllib.request import urlretrieve

import nzb2media
from nzb2media import github_api as github

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


class CheckVersion:
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
        if os.path.exists(os.path.join(nzb2media.APP_ROOT, '.git')):
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
        if not nzb2media.VERSION_NOTIFY and not force:
            log.info('Version checking is disabled, not checking for the newest version')
            return False

        log.info(f'Checking if {self.install_type} needs an update')
        if not self.updater.need_update():
            nzb2media.NEWEST_VERSION_STRING = None
            log.info('No update needed')
            return False

        self.updater.set_newest_text()
        return True

    def update(self):
        if self.updater.need_update():
            result = self.updater.update()
            return result


class UpdateManager:
    def get_github_repo_user(self):
        return nzb2media.GIT_USER

    def get_github_repo(self):
        return nzb2media.GIT_REPO

    def get_github_branch(self):
        return nzb2media.GIT_BRANCH


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
        log.debug('Unable to find your git executable - Set git_path in your autoProcessMedia.cfg OR delete your .git folder and run from source to enable updates.')

    def _find_working_git(self):
        test_cmd = 'version'

        if nzb2media.GIT_PATH:
            main_git = f'"{nzb2media.GIT_PATH}"'
        else:
            main_git = 'git'

        log.debug(f'Checking if we can use git commands: {main_git} {test_cmd}')
        output, err, exit_status = self._run_git(main_git, test_cmd)

        if exit_status == 0:
            log.debug(f'Using: {main_git}')
            return main_git
        log.debug(f'Not using: {main_git}')

        # trying alternatives

        alternative_git = []

        # osx people who start SB from launchd have a broken path, so try a hail-mary attempt for them
        if platform.system().lower() == 'darwin':
            alternative_git.append('/usr/local/git/bin/git')

        if platform.system().lower() == 'windows':
            if main_git != main_git.lower():
                alternative_git.append(main_git.lower())

        if alternative_git:
            log.debug('Trying known alternative git locations')

            for cur_git in alternative_git:
                log.debug(f'Checking if we can use git commands: {cur_git} {test_cmd}')
                output, err, exit_status = self._run_git(cur_git, test_cmd)

                if exit_status == 0:
                    log.debug(f'Using: {cur_git}')
                    return cur_git
                log.debug(f'Not using: {cur_git}')

        # Still haven't found a working git
        log.debug(
            'Unable to find your git executable - '
            'Set git_path in your autoProcessMedia.cfg OR '
            'delete your .git folder and run from source to enable updates.',
        )

        return None

    def _run_git(self, git_path, args):

        proc_out = None
        proc_err = None

        if not git_path:
            log.debug('No git specified, can\'t use git commands')
            proc_status = 1
            return proc_out, proc_err, proc_status

        cmd = f'{git_path} {args}'

        try:
            log.debug(f'Executing {cmd} with your shell in {nzb2media.APP_ROOT}')
            proc = subprocess.Popen(
                cmd,
                stdin=PIPE,
                stdout=PIPE,
                stderr=STDOUT,
                shell=True,
                cwd=nzb2media.APP_ROOT,
            )
            proc_out, proc_err = proc.communicate()
            proc_status = proc.returncode

            proc_out = proc_out.decode('utf-8')

            if proc_out:
                proc_out = proc_out.strip()
            if nzb2media.LOG_GIT:
                log.debug(f'git output: {proc_out}')

        except OSError:
            log.error(f'Command {cmd} didn\'t work')
            proc_status = 1

        proc_status = 128 if ('fatal:' in proc_out) or proc_err else proc_status
        if proc_status == 0:
            log.debug(f'{cmd} : returned successful')
            proc_status = 0
        elif nzb2media.LOG_GIT and proc_status in (1, 128):
            log.debug(f'{cmd} returned : {proc_out}')
        else:
            if nzb2media.LOG_GIT:
                log.debug(f'{cmd} returned : {proc_out}, treat as error for now')
            proc_status = 1

        return proc_out, proc_err, proc_status

    def _find_installed_version(self):
        """
        Attempt to find the currently installed version of Sick Beard.

        Uses git show to get commit version.

        Returns: True for success or False for failure
        """
        output, err, exit_status = self._run_git(
            self._git_path, 'rev-parse HEAD',
        )  # @UnusedVariable

        if exit_status == 0 and output:
            cur_commit_hash = output.strip()
            if not re.match('^[a-z0-9]+$', cur_commit_hash):
                log.error('Output doesn\'t look like a hash, not using it')
                return False
            self._cur_commit_hash = cur_commit_hash
            if self._cur_commit_hash:
                nzb2media.NZBTOMEDIA_VERSION = self._cur_commit_hash
            return True
        return False

    def _find_git_branch(self):
        nzb2media.NZBTOMEDIA_BRANCH = self.get_github_branch()
        branch_info, err, exit_status = self._run_git(
            self._git_path, 'symbolic-ref -q HEAD',
        )  # @UnusedVariable
        if exit_status == 0 and branch_info:
            branch = branch_info.strip().replace('refs/heads/', '', 1)
            if branch:
                nzb2media.NZBTOMEDIA_BRANCH = branch
                nzb2media.GIT_BRANCH = branch
        return nzb2media.GIT_BRANCH

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
        output, err, exit_status = self._run_git(
            self._git_path, 'fetch origin',
        )

        if not exit_status == 0:
            log.error('Unable to contact github, can\'t check for update')
            return

        # get latest commit_hash from remote
        output, err, exit_status = self._run_git(
            self._git_path, 'rev-parse --verify --quiet \'@{upstream}\'',
        )

        if exit_status == 0 and output:
            cur_commit_hash = output.strip()

            if not re.match('^[a-z0-9]+$', cur_commit_hash):
                log.debug('Output doesn\'t look like a hash, not using it')
                return
            self._newest_commit_hash = cur_commit_hash
        else:
            log.debug('git didn\'t return newest commit hash')
            return

        # get number of commits behind and ahead (option --count not supported git < 1.7.2)
        output, err, exit_status = self._run_git(
            self._git_path, 'rev-list --left-right \'@{upstream}\'...HEAD',
        )

        if exit_status == 0 and output:

            try:
                self._num_commits_behind = int(output.count('<'))
                self._num_commits_ahead = int(output.count('>'))

            except Exception:
                log.debug('git didn\'t return numbers for behind and ahead, not using it')
                return

        log.debug(f'cur_commit = {self._cur_commit_hash} % (newest_commit)= {self._newest_commit_hash}, num_commits_behind = {self._num_commits_behind}, num_commits_ahead = {self._num_commits_ahead}')

    def set_newest_text(self):
        if self._num_commits_ahead:
            log.error(f'Local branch is ahead of {self.branch}. Automatic update not possible.')
        elif self._num_commits_behind:
            log.info('There is a newer version available (you\'re {x} commit{s} behind)'.format(x=self._num_commits_behind, s='s' if self._num_commits_behind > 1 else ''))
        else:
            return

    def need_update(self):
        if not self._find_installed_version():
            log.error('Unable to determine installed version via git, please check your logs!')
            return False

        if not self._cur_commit_hash:
            return True

        try:
            self._check_github_for_update()
        except Exception as error:
            log.error(f'Unable to contact github, can\'t check for update: {error!r}')
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
        output, err, exit_status = self._run_git(
            self._git_path, f'pull origin {self.branch}',
        )  # @UnusedVariable

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

        version_file = os.path.join(nzb2media.APP_ROOT, 'version.txt')

        if not os.path.isfile(version_file):
            self._cur_commit_hash = None
            return

        try:
            with open(version_file) as fin:
                self._cur_commit_hash = fin.read().strip(' \n\r')
        except OSError as error:
            log.debug(f'Unable to open \'version.txt\': {error}')

        if not self._cur_commit_hash:
            self._cur_commit_hash = None
        else:
            nzb2media.NZBTOMEDIA_VERSION = self._cur_commit_hash

    def need_update(self):

        self._find_installed_version()

        try:
            self._check_github_for_update()
        except Exception as error:
            log.error(f'Unable to contact github, can\'t check for update: {error!r}')
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

        repository = github.GitHub(
            self.github_repo_user, self.github_repo, self.branch,
        )

        # try to get newest commit hash and commits behind directly by
        # comparing branch and current commit
        if self._cur_commit_hash:
            branch_compared = repository.compare(
                base=self.branch, head=self._cur_commit_hash,
            )

            if 'base_commit' in branch_compared:
                self._newest_commit_hash = branch_compared['base_commit'][
                    'sha'
                ]

            if 'behind_by' in branch_compared:
                self._num_commits_behind = int(branch_compared['behind_by'])

        # fall back and iterate over last 100 (items per page in gh_api) commits
        if not self._newest_commit_hash:

            for cur_commit in repository.commits():
                if not self._newest_commit_hash:
                    self._newest_commit_hash = cur_commit['sha']
                    if not self._cur_commit_hash:
                        break

                if cur_commit['sha'] == self._cur_commit_hash:
                    break

                # when _cur_commit_hash doesn't match anything _num_commits_behind == 100
                self._num_commits_behind += 1

        log.debug(f'cur_commit = {self._cur_commit_hash} % (newest_commit)= {self._newest_commit_hash}, num_commits_behind = {self._num_commits_behind}')

    def set_newest_text(self):

        # if we're up to date then don't set this
        nzb2media.NEWEST_VERSION_STRING = None

        if not self._cur_commit_hash:
            log.error('Unknown current version number, don\'t know if we should update or not')
        elif self._num_commits_behind > 0:
            log.info('There is a newer version available (you\'re {x} commit{s} behind)'.format(x=self._num_commits_behind, s='s' if self._num_commits_behind > 1 else ''))
        else:
            return

    def update(self):
        """Download and install latest source tarball from github."""
        tar_download_url = (
            f'https://github.com/{self.github_repo_user}/{self.github_repo}/tarball/{self.branch}'
        )
        version_path = os.path.join(nzb2media.APP_ROOT, 'version.txt')

        try:
            # prepare the update dir
            sb_update_dir = os.path.join(nzb2media.APP_ROOT, 'sb-update')

            if os.path.isdir(sb_update_dir):
                log.info(f'Clearing out update folder {sb_update_dir} before extracting')
                shutil.rmtree(sb_update_dir)

            log.info(f'Creating update folder {sb_update_dir} before extracting')
            os.makedirs(sb_update_dir)

            # retrieve file
            log.info(f'Downloading update from {tar_download_url!r}')
            tar_download_path = os.path.join(
                sb_update_dir, 'nzbtomedia-update.tar',
            )
            urlretrieve(tar_download_url, tar_download_path)

            if not os.path.isfile(tar_download_path):
                log.error(f'Unable to retrieve new version from {tar_download_url}, can\'t update')
                return False

            if not tarfile.is_tarfile(tar_download_path):
                log.error(f'Retrieved version from {tar_download_url} is corrupt, can\'t update')
                return False

            # extract to sb-update dir
            log.info(f'Extracting file {tar_download_path}')
            tar = tarfile.open(tar_download_path)
            tar.extractall(sb_update_dir)
            tar.close()

            # delete .tar.gz
            log.info(f'Deleting file {tar_download_path}')
            os.remove(tar_download_path)

            # find update dir name
            update_dir_contents = [
                x
                for x in os.listdir(sb_update_dir)
                if os.path.isdir(os.path.join(sb_update_dir, x))
            ]
            if len(update_dir_contents) != 1:
                log.error(f'Invalid update data, update failed: {update_dir_contents}')
                return False
            content_dir = os.path.join(sb_update_dir, update_dir_contents[0])

            # walk temp folder and move files to main folder
            log.info(f'Moving files from {content_dir} to {nzb2media.APP_ROOT}')
            for dirname, _, filenames in os.walk(
                content_dir,
            ):  # @UnusedVariable
                dirname = dirname[len(content_dir) + 1:]
                for curfile in filenames:
                    old_path = os.path.join(content_dir, dirname, curfile)
                    new_path = os.path.join(nzb2media.APP_ROOT, dirname, curfile)

                    # Avoid DLL access problem on WIN32/64
                    # These files needing to be updated manually
                    # or find a way to kill the access from memory
                    if curfile in ('unrar.dll', 'unrar64.dll'):
                        try:
                            os.chmod(new_path, stat.S_IWRITE)
                            os.remove(new_path)
                            os.renames(old_path, new_path)
                        except Exception as error:
                            log.debug(f'Unable to update {new_path}: {error}')
                            # Trash the updated file without moving in new path
                            os.remove(old_path)
                        continue

                    if os.path.isfile(new_path):
                        os.remove(new_path)
                    os.renames(old_path, new_path)

            # update version.txt with commit hash
            try:
                with open(version_path, 'w') as ver_file:
                    ver_file.write(self._newest_commit_hash)
            except OSError as error:
                log.error(f'Unable to write version file, update not complete: {error}')
                return False

        except Exception as error:
            log.error(f'Error while trying to update: {error}')
            log.debug(f'Traceback: {traceback.format_exc()}')
            return False

        return True
