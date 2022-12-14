from __future__ import annotations

import os

import core
from core import logger
from core.auto_process.common import ProcessResult
from core.processor import nzb
from core.utils.common import get_dirs
from core.utils.download_info import get_download_info


def process():
    # Perform Manual Post-Processing
    logger.warning(
        'Invalid number of arguments received from client, Switching to manual run mode ...',
    )

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
                    f'Starting manual run for {section}:{subsection} - Folder: {dir_name}',
                )
                logger.info(
                    f'Checking database for download info for {os.path.basename(dir_name)} ...',
                )

                core.DOWNLOAD_INFO = get_download_info(
                    os.path.basename(dir_name),
                    0,
                )
                if core.DOWNLOAD_INFO:
                    logger.info(
                        f'Found download info for {os.path.basename(dir_name)}, setting variables now ...',
                    )
                    client_agent = (
                        core.DOWNLOAD_INFO[0]['client_agent'] or 'manual'
                    )
                    download_id = core.DOWNLOAD_INFO[0]['input_id'] or ''
                else:
                    logger.info(
                        f'Unable to locate download info for {os.path.basename(dir_name)}, continuing to try and process this release ...',
                    )
                    client_agent = 'manual'
                    download_id = ''

                if (
                    client_agent
                    and client_agent.lower() not in core.NZB_CLIENTS
                ):
                    continue

                input_name = os.path.basename(dir_name)

                results = nzb.process(
                    dir_name,
                    input_name,
                    0,
                    client_agent=client_agent,
                    download_id=download_id or None,
                    input_category=subsection,
                )
                if results.status_code != 0:
                    logger.error(
                        f'A problem was reported when trying to perform a manual run for {section}:{subsection}.',
                    )
                    result = results
    return result
