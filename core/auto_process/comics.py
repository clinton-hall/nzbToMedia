# coding=utf-8

from __future__ import (
    absolute_import,
    division,
    print_function,
    unicode_literals,
)

import os

import requests

import core
from core import logger
from core.auto_process.common import ProcessResult
from core.utils import convert_to_ascii, remote_dir, server_responding

requests.packages.urllib3.disable_warnings()


def process(section, dir_name, input_name=None, status=0, client_agent='manual', input_category=None):
    apc_version = '2.04'
    comicrn_version = '1.01'

    cfg = dict(core.CFG[section][input_category])

    host = cfg['host']
    port = cfg['port']
    apikey = cfg['apikey']
    ssl = int(cfg.get('ssl', 0))
    web_root = cfg.get('web_root', '')
    remote_path = int(cfg.get('remote_path'), 0)
    protocol = 'https://' if ssl else 'http://'

    url = '{0}{1}:{2}{3}/api'.format(protocol, host, port, web_root)
    if not server_responding(url):
        logger.error('Server did not respond. Exiting', section)
        return ProcessResult(
            message='{0}: Failed to post-process - {0} did not respond.'.format(section),
            status_code=1,
        )

    input_name, dir_name = convert_to_ascii(input_name, dir_name)
    clean_name, ext = os.path.splitext(input_name)
    if len(ext) == 4:  # we assume this was a standard extension.
        input_name = clean_name

    params = {
        'cmd': 'forceProcess',
        'apikey': apikey,
        'nzb_folder': remote_dir(dir_name) if remote_path else dir_name,
    }

    if input_name is not None:
        params['nzb_name'] = input_name
    params['failed'] = int(status)
    params['apc_version'] = apc_version
    params['comicrn_version'] = comicrn_version

    success = False

    logger.debug('Opening URL: {0}'.format(url), section)
    try:
        r = requests.post(url, params=params, stream=True, verify=False, timeout=(30, 300))
    except requests.ConnectionError:
        logger.error('Unable to open URL', section)
        return ProcessResult(
            message='{0}: Failed to post-process - Unable to connect to {0}'.format(section),
            status_code=1,
        )
    if r.status_code not in [requests.codes.ok, requests.codes.created, requests.codes.accepted]:
        logger.error('Server returned status {0}'.format(r.status_code), section)
        return ProcessResult(
            message='{0}: Failed to post-process - Server returned status {1}'.format(section, r.status_code),
            status_code=1,
        )

    result = r.text
    if not type(result) == list:
        result = result.split('\n')
    for line in result:
        if line:
            logger.postprocess('{0}'.format(line), section)
        if 'Post Processing SUCCESSFUL' in line:
            success = True

    if success:
        logger.postprocess('SUCCESS: This issue has been processed successfully', section)
        return ProcessResult(
            message='{0}: Successfully post-processed {1}'.format(section, input_name),
            status_code=0,
        )
    else:
        logger.warning('The issue does not appear to have successfully processed. Please check your Logs', section)
        return ProcessResult(
            message='{0}: Failed to post-process - Returned log from {0} was not as expected.'.format(section),
            status_code=1,
        )
