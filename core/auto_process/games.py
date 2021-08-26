# coding=utf-8

from __future__ import (
    absolute_import,
    division,
    print_function,
    unicode_literals,
)

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
    library = cfg.get('library')
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

    fields = input_name.split('-')

    gamez_id = fields[0].replace('[', '').replace(']', '').replace(' ', '')

    download_status = 'Downloaded' if status == 0 else 'Wanted'

    params = {
        'api_key': apikey,
        'mode': 'UPDATEREQUESTEDSTATUS',
        'db_id': gamez_id,
        'status': download_status,
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
    if library:
        logger.postprocess('moving files to library: {0}'.format(library), section)
        try:
            shutil.move(dir_name, os.path.join(library, input_name))
        except Exception:
            logger.error('Unable to move {0} to {1}'.format(dir_name, os.path.join(library, input_name)), section)
            return ProcessResult(
                message='{0}: Failed to post-process - Unable to move files'.format(section),
                status_code=1,
            )
    else:
        logger.error('No library specified to move files to. Please edit your configuration.', section)
        return ProcessResult(
            message='{0}: Failed to post-process - No library defined in {0}'.format(section),
            status_code=1,
        )

    if r.status_code not in [requests.codes.ok, requests.codes.created, requests.codes.accepted]:
        logger.error('Server returned status {0}'.format(r.status_code), section)
        return ProcessResult(
            message='{0}: Failed to post-process - Server returned status {1}'.format(section, r.status_code),
            status_code=1,
        )
    elif result['success']:
        logger.postprocess('SUCCESS: Status for {0} has been set to {1} in Gamez'.format(gamez_id, download_status), section)
        return ProcessResult(
            message='{0}: Successfully post-processed {1}'.format(section, input_name),
            status_code=0,
        )
    else:
        logger.error('FAILED: Status for {0} has NOT been updated in Gamez'.format(gamez_id), section)
        return ProcessResult(
            message='{0}: Failed to post-process - Returned log from {0} was not as expected.'.format(section),
            status_code=1,
        )
