# coding=utf-8

from __future__ import (
    absolute_import,
    division,
    print_function,
    unicode_literals,
)

import requests
from six import iteritems

import core
from core import logger

def api_check(r, params, rem_params):
    try:
        json_data = r.json()
    except ValueError:
        logger.error('Failed to get JSON data from response')
        logger.debug('Response received')
        raise

    if isinstance(json_data, str):
        return rem_params, False

    try:
        json_data = json_data['data']
    except KeyError:
        logger.error('Failed to get data from JSON')
        logger.debug('Response received: {}'.format(json_data))
        raise
    else:
        json_data = json_data.get('data', json_data)

    try:
        optional_parameters = json_data['optionalParameters'].keys()
        # Find excess parameters
        excess_parameters = set(params).difference(optional_parameters)
        logger.debug('Removing excess parameters: {}'.format(sorted(excess_parameters)))
        rem_params.extend(excess_parameters)
        return rem_params, True
    except:
        logger.error('Failed to identify optionalParameters')
        return rem_params, False


def auto_fork(section, input_category):
    # auto-detect correct section
    # config settings
    if core.FORK_SET: # keep using determined fork for multiple (manual) post-processing
        logger.info('{section}:{category} fork already set to {fork}'.format
                    (section=section, category=input_category, fork=core.FORK_SET[0]))
        return core.FORK_SET[0], core.FORK_SET[1]

    cfg = dict(core.CFG[section][input_category])

    host = cfg.get('host')
    port = cfg.get('port')
    username = cfg.get('username')
    password = cfg.get('password')
    apikey = cfg.get('apikey')
    ssl = int(cfg.get('ssl', 0))
    web_root = cfg.get('web_root', '')
    replace = {
        'medusa': 'Medusa',
        'medusa-api': 'Medusa-api',
        'sickbeard-api': 'SickBeard-api',
        'sickgear': 'SickGear',
        'sickchill': 'SickChill',
        'sickrage': 'SickRage',
        'stheno': 'Stheno',
    }
    _val = cfg.get('fork', 'auto')
    f1 = replace.get(_val, _val)
    try:
        fork = f1, core.FORKS[f1]
    except KeyError:
        fork = 'auto'
    protocol = 'https://' if ssl else 'http://'

    detected = False
    if section == 'NzbDrone':
        logger.info('Attempting to verify {category} fork'.format
                    (category=input_category))
        url = '{protocol}{host}:{port}{root}/api/rootfolder'.format(
            protocol=protocol, host=host, port=port, root=web_root,
        )
        headers = {'X-Api-Key': apikey}
        try:
            r = requests.get(url, headers=headers, stream=True, verify=False)
        except requests.ConnectionError:
            logger.warning('Could not connect to {0}:{1} to verify fork!'.format(section, input_category))

        if not r.ok:
            logger.warning('Connection to {section}:{category} failed! '
                           'Check your configuration'.format
                           (section=section, category=input_category))

        fork = ['default', {}]

    elif fork == 'auto':
        params = core.ALL_FORKS
        rem_params = []
        logger.info('Attempting to auto-detect {category} fork'.format(category=input_category))
        # define the order to test. Default must be first since the default fork doesn't reject parameters.
        # then in order of most unique parameters.

        if apikey:
            url = '{protocol}{host}:{port}{root}/api/{apikey}/?cmd=sg.postprocess&help=1'.format(
                protocol=protocol, host=host, port=port, root=web_root, apikey=apikey,
            )
        else:
            url = '{protocol}{host}:{port}{root}/home/postprocess/'.format(
                protocol=protocol, host=host, port=port, root=web_root,
            )

        # attempting to auto-detect fork
        try:
            s = requests.Session()
            if not apikey and username and password:
                login = '{protocol}{host}:{port}{root}/login'.format(
                    protocol=protocol, host=host, port=port, root=web_root)
                login_params = {'username': username, 'password': password}
                r = s.get(login, verify=False, timeout=(30, 60))
                if r.status_code in [401, 403] and r.cookies.get('_xsrf'):
                    login_params['_xsrf'] = r.cookies.get('_xsrf')
                s.post(login, data=login_params, stream=True, verify=False)
            r = s.get(url, auth=(username, password), verify=False)
        except requests.ConnectionError:
            logger.info('Could not connect to {section}:{category} to perform auto-fork detection!'.format
                        (section=section, category=input_category))
            r = []
        if r and r.ok:
            if apikey:
                rem_params, found = api_check(r, params, rem_params)
                if found:
                    params['cmd'] = 'sg.postprocess'
                else: # try different api set for non-SickGear forks.
                    url = '{protocol}{host}:{port}{root}/api/{apikey}/?cmd=help&subject=postprocess'.format(
                        protocol=protocol, host=host, port=port, root=web_root, apikey=apikey,
                    )
                    try:
                        r = s.get(url, auth=(username, password), verify=False)
                    except requests.ConnectionError:
                        logger.info('Could not connect to {section}:{category} to perform auto-fork detection!'.format
                                    (section=section, category=input_category))
                    rem_params, found = api_check(r, params, rem_params)
                    params['cmd'] = 'postprocess'
            else:
                # Find excess parameters
                rem_params.extend(
                    param
                    for param in params
                    if 'name="{param}"'.format(param=param) not in r.text
                )

            # Remove excess params
            for param in rem_params:
                params.pop(param)

            for fork in sorted(iteritems(core.FORKS), reverse=False):
                if params == fork[1]:
                    detected = True
                    break

        if detected:
            logger.info('{section}:{category} fork auto-detection successful ...'.format
                        (section=section, category=input_category))
        elif rem_params:
            logger.info('{section}:{category} fork auto-detection found custom params {params}'.format
                        (section=section, category=input_category, params=params))
            fork = ['custom', params]
        else:
            logger.info('{section}:{category} fork auto-detection failed'.format
                        (section=section, category=input_category))
            fork = list(core.FORKS.items())[list(core.FORKS.keys()).index(core.FORK_DEFAULT)]


    logger.info('{section}:{category} fork set to {fork}'.format
                (section=section, category=input_category, fork=fork[0]))
    core.FORK_SET = fork
    return fork[0], fork[1]
