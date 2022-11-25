import os
import sys

import core
from core import logger
from core.processor import nzb


def process():
    # Check if the script is called from nzbget 11.0 or later
    if os.environ['NZBOP_VERSION'][0:5] < '11.0':
        logger.error(
            'NZBGet Version {0} is not supported. Please update NZBGet.'.format(
                os.environ['NZBOP_VERSION']))
        sys.exit(core.NZBGET_POSTPROCESS_ERROR)

    logger.info('Script triggered from NZBGet Version {0}.'.format(
        os.environ['NZBOP_VERSION']))

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

    # Check for download_id to pass to CouchPotato
    download_id = ''
    failure_link = None
    if 'NZBPR_COUCHPOTATO' in os.environ:
        download_id = os.environ['NZBPR_COUCHPOTATO']
    elif 'NZBPR_DRONE' in os.environ:
        download_id = os.environ['NZBPR_DRONE']
    elif 'NZBPR_SONARR' in os.environ:
        download_id = os.environ['NZBPR_SONARR']
    elif 'NZBPR_RADARR' in os.environ:
        download_id = os.environ['NZBPR_RADARR']
    elif 'NZBPR_LIDARR' in os.environ:
        download_id = os.environ['NZBPR_LIDARR']
    if 'NZBPR__DNZB_FAILURE' in os.environ:
        failure_link = os.environ['NZBPR__DNZB_FAILURE']

    # All checks done, now launching the script.
    client_agent = 'nzbget'
    return nzb.process(
        os.environ['NZBPP_DIRECTORY'],
        input_name=os.environ['NZBPP_NZBNAME'],
        status=status,
        client_agent=client_agent,
        download_id=download_id,
        input_category=os.environ['NZBPP_CATEGORY'],
        failure_link=failure_link,
    )
