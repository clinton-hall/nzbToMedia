# coding=utf-8

import requests

from six import iteritems

import core
from core import logger


def autoFork(section, inputCategory):
    # auto-detect correct section
    # config settings

    cfg = dict(core.CFG[section][inputCategory])

    host = cfg.get("host")
    port = cfg.get("port")
    username = cfg.get("username")
    password = cfg.get("password")
    apikey = cfg.get("apikey")
    ssl = int(cfg.get("ssl", 0))
    web_root = cfg.get("web_root", "")
    replace = {'sickrage':'SickRage', 'sickchill':'SickChill', 'sickgear':'SickGear', 'medusa':'Medusa', 'sickbeard-api':'SickBeard-api'}
    f1 = replace[cfg.get("fork", "auto")] if cfg.get("fork", "auto") in replace else cfg.get("fork", "auto")
    try:
        fork = core.FORKS.items()[core.FORKS.keys().index(f1)]
    except:
        fork = "auto"
    protocol = "https://" if ssl else "http://"

    detected = False
    if section == "NzbDrone":
        logger.info("Attempting to verify {category} fork".format
                    (category=inputCategory))
        url = "{protocol}{host}:{port}{root}/api/rootfolder".format(
                    protocol=protocol, host=host, port=port, root=web_root)
        headers = {"X-Api-Key": apikey}
        try:
            r = requests.get(url, headers=headers, stream=True, verify=False)
        except requests.ConnectionError:
            logger.warning("Could not connect to {0}:{1} to verify fork!".format(section, inputCategory))

        if not r.ok:
            logger.warning("Connection to {section}:{category} failed! "
                           "Check your configuration".format
                           (section=section, category=inputCategory))

        fork = ['default', {}]

    elif fork == "auto":
        params = core.ALL_FORKS
        rem_params = []
        logger.info("Attempting to auto-detect {category} fork".format(category=inputCategory))
        # define the order to test. Default must be first since the default fork doesn't reject parameters.
        # then in order of most unique parameters.

        if apikey:
            url = "{protocol}{host}:{port}{root}/api/{apikey}/?cmd=help&subject=postprocess".format(
                        protocol=protocol, host=host, port=port, root=web_root, apikey=apikey)
        else:
            url = "{protocol}{host}:{port}{root}/home/postprocess/".format(
                        protocol=protocol, host=host, port=port, root=web_root)

        # attempting to auto-detect fork
        try:
            s = requests.Session()
            if not apikey and username and password:
                login = "{protocol}{host}:{port}{root}/login".format(
                    protocol=protocol, host=host, port=port, root=web_root)
                login_params = {'username': username, 'password': password}
                r = s.get(login, verify=False, timeout=(30,60))
                if r.status_code == 401 and r.cookies.get('_xsrf'):
                    login_params['_xsrf'] = r.cookies.get('_xsrf')
                s.post(login, data=login_params, stream=True, verify=False)
            r = s.get(url, auth=(username, password), verify=False)
        except requests.ConnectionError:
            logger.info("Could not connect to {section}:{category} to perform auto-fork detection!".format
                        (section=section, category=inputCategory))
            r = []
        if r and r.ok:
            if apikey:
                optionalParameters = []
                try:
                    optionalParameters = r.json()['data']['optionalParameters'].keys()
                except:
                    optionalParameters = r.json()['data']['data']['optionalParameters'].keys()
                for param in params:
                    if param not in optionalParameters:
                        rem_params.append(param)
            else:
                for param in params:
                    if 'name="{param}"'.format(param=param) not in r.text:
                        rem_params.append(param)
            for param in rem_params:
                params.pop(param)
            for fork in sorted(iteritems(core.FORKS), reverse=False):
                if params == fork[1]:
                    detected = True
                    break
        if detected:
            logger.info("{section}:{category} fork auto-detection successful ...".format
                        (section=section, category=inputCategory))
        elif rem_params:
            logger.info("{section}:{category} fork auto-detection found custom params {params}".format
                        (section=section, category=inputCategory, params=params))
            fork = ['custom', params]
        else:
            logger.info("{section}:{category} fork auto-detection failed".format
                        (section=section, category=inputCategory))
            fork = core.FORKS.items()[core.FORKS.keys().index(core.FORK_DEFAULT)]

    logger.info("{section}:{category} fork set to {fork}".format
                (section=section, category=inputCategory, fork=fork[0]))
    return fork[0], fork[1]
