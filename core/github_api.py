# coding=utf-8

from __future__ import (
    absolute_import,
    division,
    print_function,
    unicode_literals,
)

import requests


class GitHub(object):
    """Simple api wrapper for the Github API v3."""

    def __init__(self, github_repo_user, github_repo, branch='master'):

        self.github_repo_user = github_repo_user
        self.github_repo = github_repo
        self.branch = branch

    def _access_api(self, path, params=None):
        """Access API at given an API path and optional parameters."""
        url = 'https://api.github.com/{path}'.format(path='/'.join(path))
        data = requests.get(url, params=params, verify=False)
        return data.json() if data.ok else []

    def commits(self):
        """
        Get the 100 most recent commits from the specified user/repo/branch, starting from HEAD.

        user: The github username of the person whose repo you're querying
        repo: The repo name to query
        branch: Optional, the branch name to show commits from

        Returns a deserialized json object containing the commit info. See http://developer.github.com/v3/repos/commits/
        """
        return self._access_api(
            ['repos', self.github_repo_user, self.github_repo, 'commits'],
            params={'per_page': 100, 'sha': self.branch},
        )

    def compare(self, base, head, per_page=1):
        """
        Get compares between base and head.

        user: The github username of the person whose repo you're querying
        repo: The repo name to query
        base: Start compare from branch
        head: Current commit sha or branch name to compare
        per_page: number of items per page

        Returns a deserialized json object containing the compare info. See http://developer.github.com/v3/repos/commits/
        """
        return self._access_api(
            ['repos', self.github_repo_user, self.github_repo, 'compare',
             '{base}...{head}'.format(base=base, head=head)],
            params={'per_page': per_page},
        )
