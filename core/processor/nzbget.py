import os
import sys

import core
from core import logger
from core.processor import nzb


def parse_download_id():
    """Parse nzbget download_id from environment."""
    download_id_keys = [
        'NZBPR_COUCHPOTATO',
        'NZBPR_DRONE',
        'NZBPR_SONARR',
        'NZBPR_RADARR',
        'NZBPR_LIDARR',
    ]
    for download_id_key in download_id_keys:
        try:
            return os.environ[download_id_key]
        except KeyError:
            pass
    else:
        return ''


def parse_failure_link():
    """Parse nzbget failure_link from environment."""
    return os.environ.get('NZBPR__DNZB_FAILURE')


def parse_status():
    status = 0
    # Check if the script is called from nzbget 13.0 or later
    if 'NZBPP_TOTALSTATUS' in os.environ:
        if not os.environ['NZBPP_TOTALSTATUS'] == 'SUCCESS':
            logger.info('Download failed with status {0}.'.format(
                os.environ['NZBPP_STATUS']))
            status = 1

    else:
        # Check par status
        if os.environ['NZBPP_PARSTATUS'] == '1' or os.environ[
            'NZBPP_PARSTATUS'] == '4':
            logger.warning('Par-repair failed, setting status \'failed\'')
            status = 1

        # Check unpack status
        if os.environ['NZBPP_UNPACKSTATUS'] == '1':
            logger.warning('Unpack failed, setting status \'failed\'')
            status = 1

        if os.environ['NZBPP_UNPACKSTATUS'] == '0' and os.environ[
            'NZBPP_PARSTATUS'] == '0':
            # Unpack was skipped due to nzb-file properties or due to errors during par-check

            if os.environ['NZBPP_HEALTH'] < 1000:
                logger.warning(
                    'Download health is compromised and Par-check/repair disabled or no .par2 files found. Setting status \'failed\'')
                logger.info(
                    'Please check your Par-check/repair settings for future downloads.')
                status = 1

            else:
                logger.info(
                    'Par-check/repair disabled or no .par2 files found, and Unpack not required. Health is ok so handle as though download successful')
                logger.info(
                    'Please check your Par-check/repair settings for future downloads.')
    return status


def check_version():
    # Check if the script is called from nzbget 11.0 or later
    if os.environ['NZBOP_VERSION'][0:5] < '11.0':
        logger.error(
            'NZBGet Version {0} is not supported. Please update NZBGet.'.format(
                os.environ['NZBOP_VERSION']))
        sys.exit(core.NZBGET_POSTPROCESS_ERROR)

    logger.info('Script triggered from NZBGet Version {0}.'.format(
        os.environ['NZBOP_VERSION']))


def process():
    check_version()
    status = parse_status()
    download_id = parse_download_id()
    failure_link = parse_failure_link()
    return nzb.process(
        input_directory=os.environ['NZBPP_DIRECTORY'],
        input_name=os.environ['NZBPP_NZBNAME'],
        status=status,
        client_agent='nzbget',
        download_id=download_id,
        input_category=os.environ['NZBPP_CATEGORY'],
        failure_link=failure_link,
    )
