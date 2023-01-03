from __future__ import annotations

import logging
import os

import nzb2media
import nzb2media.nzb
from nzb2media.auto_process.common import ProcessResult
from nzb2media.processor import nzb
from nzb2media.utils.common import get_dirs
from nzb2media.utils.download_info import get_download_info

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


def process():
    # Perform Manual Post-Processing
    log.warning('Invalid number of arguments received from client, Switching to manual run mode ...')
    # Post-Processing Result
    result = ProcessResult(message='', status_code=0)
    for section, subsections in nzb2media.SECTIONS.items():
        for subsection in subsections:
            if nzb2media.CFG[section][subsection].isenabled():
                result = _process(section, subsection)
    return result


def _process(section, subsection):
    for dir_name in get_dirs(section, subsection, link='move'):
        log.info(f'Starting manual run for {section}:{subsection} - Folder: {dir_name}')
        log.info(f'Checking database for download info for {os.path.basename(dir_name)} ...')
        download_info = get_download_info(os.path.basename(dir_name), 0)
        nzb2media.DOWNLOAD_INFO = download_info
        if download_info:
            log.info(f'Found download info for {os.path.basename(dir_name)}, setting variables now ...')
        else:
            log.info(f'Unable to locate download info for {os.path.basename(dir_name)}, continuing to try and process this release ...')
        client_agent, download_id = _process_download_info(nzb2media.DOWNLOAD_INFO)
        if client_agent != 'manual' and client_agent.lower() not in nzb2media.nzb.CLIENTS:
            continue
        input_name = os.path.basename(dir_name)
        result = nzb.process(input_directory=dir_name, input_name=input_name, client_agent=client_agent, download_id=download_id or None, input_category=subsection)
        if result.status_code:
            log.error(f'A problem was reported when trying to perform a manual run for {section}:{subsection}.')
            return result


def _process_download_info(download_info):
    agent = None
    download_id = None
    if not download_info:
        agent = download_info[0]['client_agent']
        download_id = download_info[0]['input_id']
    return agent or 'manual', download_id or ''
