# coding=utf-8

import os
import shutil

import requests

import core
from core import logger
from core.auto_process.common import ProcessResult
from core.utils import convert_to_ascii, server_responding

requests.packages.urllib3.disable_warnings()


def process(section, dir_name, input_name=None, status=0, client_agent='manual', input_category=None):
    status = int(status)

    cfg = dict(core.CFG[section][input_category])

    host = cfg['host']
    port = cfg['port']
    apikey = cfg['apikey']
    ssl = int(cfg.get('ssl', 0))
    web_root = cfg.get('web_root', '')
    protocol = 'https://' if ssl else 'http://'

    url = '{0}{1}:{2}{3}/api'.format(protocol, host, port, web_root)
    if not server_responding(url):
        logger.error('Server did not respond. Exiting', section)
        return ProcessResult(
            message='{0}: Failed to post-process - {0} did not respond.'.format(section),
            status_code=1,
        )

    input_name, dir_name = convert_to_ascii(input_name, dir_name)

    params = {
        'api_key': apikey,
        'cmd': 'forceProcess',
        'dir': dir_name,
    }

    logger.debug('Opening URL: {0}'.format(url), section)

    try:
        r = requests.get(url, params=params, verify=False, timeout=(30, 300))
    except requests.ConnectionError:
        logger.error('Unable to open URL')
        return ProcessResult(
            message='{0}: Failed to post-process - Unable to connect to {1}'.format(section, section),
            status_code=1,
        )

    result = r.json()
    logger.postprocess('{0}'.format(result), section)
 
    if r.status_code not in [requests.codes.ok, requests.codes.created, requests.codes.accepted]:
        logger.error('Server returned status {0}'.format(r.status_code), section)
        return ProcessResult(
            message='{0}: Failed to post-process - Server returned status {1}'.format(section, r.status_code),
            status_code=1,
        )
    elif result['success']:
        logger.postprocess('SUCCESS: ForceProcess for {0} has been started in LazyLibrarian'.format(dir_name), section)
        return ProcessResult(
            message='{0}: Successfully post-processed {1}'.format(section, input_name),
            status_code=0,
        )
    else:
        logger.error('FAILED: ForceProcess of {0} has Failed in LazyLibrarian'.format(dir_name), section)
        return ProcessResult(
            message='{0}: Failed to post-process - Returned log from {0} was not as expected.'.format(section),
            status_code=1,
        )
