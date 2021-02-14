import requests

from core import logger

from .sickbeard import SickBeard


class PyMedusa(SickBeard):
    """PyMedusa class."""

    def __init__(self, sb_init):
        super(PyMedusa, self).__init__(sb_init)
        self.cfg = self.sb_init.config  # in case we need something that's not already directly on self.sb_init.

    def _configure():
        """Configure pymedusa with config options."""

    def _create_url(self):
        if self.sb_init.apikey:
            return '{0}{1}:{2}{3}/api/{4}/'.format(self.sb_init.protocol, self.sb_init.host, self.sb_init.port, self.sb_init.web_root, self.sb_init.apikey)
        return '{0}{1}:{2}{3}/home/postprocess/processEpisode'.format(self.sb_init.protocol, self.sb_init.host, self.sb_init.port, self.sb_init.web_root)

    def api_call(self):
        """Perform the api call with PyMedusa."""
        s = requests.Session()

        self._process_fork_prarams()
        url = self._create_url()

        logger.debug('Opening URL: {0} with params: {1}'.format(url, self.sb_init.fork_params), self.sb_init.section)
        if not self.sb_init.apikey and self.sb_init.username and self.sb_init.password:
            login = '{0}{1}:{2}{3}/login'.format(self.sb_init.protocol, self.sb_init.host, self.sb_init.port, self.sb_init.web_root)
            login_params = {'username': self.sb_init.username, 'password': self.sb_init.password}
            r = s.get(login, verify=False, timeout=(30, 60))
            if r.status_code in [401, 403] and r.cookies.get('_xsrf'):
                login_params['_xsrf'] = r.cookies.get('_xsrf')
            s.post(login, data=login_params, stream=True, verify=False, timeout=(30, 60))
        return s.get(url, auth=(self.sb_init.username, self.sb_init.password), params=self.sb_init.fork_params, stream=True, verify=False, timeout=(30, 1800))
