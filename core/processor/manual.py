import os

import core
from core import logger
from core.auto_process.common import ProcessResult
from core.processor import nzb
from core.utils import (
    get_dirs,
    get_download_info,
)

try:
    text_type = unicode
except NameError:
    text_type = str


def process():
    # Perform Manual Post-Processing
    logger.warning(
        'Invalid number of arguments received from client, Switching to manual run mode ...')

    # Post-Processing Result
    result = ProcessResult(
        message='',
        status_code=0,
    )

    for section, subsections in core.SECTIONS.items():
        for subsection in subsections:
            if not core.CFG[section][subsection].isenabled():
                continue
            for dir_name in get_dirs(section, subsection, link='move'):
                logger.info(
                    'Starting manual run for {0}:{1} - Folder: {2}'.format(
                        section, subsection, dir_name))
                logger.info(
                    'Checking database for download info for {0} ...'.format(
                        os.path.basename(dir_name)))

                core.DOWNLOAD_INFO = get_download_info(
                    os.path.basename(dir_name), 0)
                if core.DOWNLOAD_INFO:
                    logger.info('Found download info for {0}, '
                                'setting variables now ...'.format
                                (os.path.basename(dir_name)))
                    client_agent = text_type(
                        core.DOWNLOAD_INFO[0]['client_agent']) or 'manual'
                    download_id = text_type(
                        core.DOWNLOAD_INFO[0]['input_id']) or ''
                else:
                    logger.info('Unable to locate download info for {0}, '
                                'continuing to try and process this release ...'.format
                                (os.path.basename(dir_name)))
                    client_agent = 'manual'
                    download_id = ''

                if client_agent and client_agent.lower() not in core.NZB_CLIENTS:
                    continue

                input_name = os.path.basename(dir_name)

                results = nzb.process(dir_name, input_name, 0,
                                  client_agent=client_agent,
                                  download_id=download_id or None,
                                  input_category=subsection)
                if results.status_code != 0:
                    logger.error(
                        'A problem was reported when trying to perform a manual run for {0}:{1}.'.format
                        (section, subsection))
                    result = results
    return result
