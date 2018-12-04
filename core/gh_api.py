# coding=utf-8

import requests
from six import iteritems


class GitHub(object):
    """
    Simple api wrapper for the Github API v3.
    """

    def __init__(self, github_repo_user, github_repo, branch='master'):

        self.github_repo_user = github_repo_user
        self.github_repo = github_repo
        self.branch = branch

    def _access_API(self, path, params=None):
        """
        Access the API at the path given and with the optional params given.
        """

        url = 'https://api.github.com/{path}'.format(path='/'.join(path))

        if params and type(params) is dict:
            url += '?{params}'.format(params='&'.join(['{key}={value}'.format(key=k, value=v)
                                                       for k, v in iteritems(params)]))

        data = requests.get(url, verify=False)

        if data.ok:
            json_data = data.json()
            return json_data
        else:
            return []

    def commits(self):
        """
        Uses the API to get a list of the 100 most recent commits from the specified user/repo/branch, starting from HEAD.

        user: The github username of the person whose repo you're querying
        repo: The repo name to query
        branch: Optional, the branch name to show commits from

        Returns a deserialized json object containing the commit info. See http://developer.github.com/v3/repos/commits/
        """
        access_API = self._access_API(['repos', self.github_repo_user, self.github_repo, 'commits'],
                                      params={'per_page': 100, 'sha': self.branch})
        return access_API

    def compare(self, base, head, per_page=1):
        """
        Uses the API to get a list of compares between base and head.

        user: The github username of the person whose repo you're querying
        repo: The repo name to query
        base: Start compare from branch
        head: Current commit sha or branch name to compare
        per_page: number of items per page

        Returns a deserialized json object containing the compare info. See http://developer.github.com/v3/repos/commits/
        """
        access_API = self._access_API(
            ['repos', self.github_repo_user, self.github_repo, 'compare', '{base}...{head}'.format(base=base, head=head)],
            params={'per_page': per_page})
        return access_API
