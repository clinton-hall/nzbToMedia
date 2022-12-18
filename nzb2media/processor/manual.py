from __future__ import annotations

import logging
import os

import nzb2media
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
            if not nzb2media.CFG[section][subsection].isenabled():
                continue
            for dir_name in get_dirs(section, subsection, link='move'):
                log.info(f'Starting manual run for {section}:{subsection} - Folder: {dir_name}')
                log.info(f'Checking database for download info for {os.path.basename(dir_name)} ...')
                nzb2media.DOWNLOAD_INFO = get_download_info(os.path.basename(dir_name), 0)
                if nzb2media.DOWNLOAD_INFO:
                    log.info(f'Found download info for {os.path.basename(dir_name)}, setting variables now ...')
                    client_agent = nzb2media.DOWNLOAD_INFO[0]['client_agent'] or 'manual'
                    download_id = nzb2media.DOWNLOAD_INFO[0]['input_id'] or ''
                else:
                    log.info(f'Unable to locate download info for {os.path.basename(dir_name)}, continuing to try and process this release ...')
                    client_agent = 'manual'
                    download_id = ''
                if client_agent and client_agent.lower() not in nzb2media.NZB_CLIENTS:
                    continue
                input_name = os.path.basename(dir_name)
                results = nzb.process(dir_name, input_name, 0, client_agent=client_agent, download_id=download_id or None, input_category=subsection)
                if results.status_code != 0:
                    log.error(f'A problem was reported when trying to perform a manual run for {section}:{subsection}.')
                    result = results
    return result
