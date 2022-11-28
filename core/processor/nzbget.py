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


def _parse_total_status():
    status_summary = os.environ['NZBPP_TOTALSTATUS']
    if status_summary != 'SUCCESS':
        status = os.environ['NZBPP_STATUS']
        logger.info('Download failed with status {0}.'.format(status))
        return 1
    return 0


def _parse_par_status():
    """Parse nzbget par status from environment."""
    par_status = os.environ['NZBPP_PARSTATUS']
    if par_status == '1' or par_status == '4':
        logger.warning('Par-repair failed, setting status \'failed\'')
        return 1
    return 0


def _parse_unpack_status():
    if os.environ['NZBPP_UNPACKSTATUS'] == '1':
        logger.warning('Unpack failed, setting status \'failed\'')
        return 1
    return 0


def _parse_health_status():
    """Parse nzbget download health from environment."""
    status = 0
    unpack_status_value = os.environ['NZBPP_UNPACKSTATUS']
    par_status_value = os.environ['NZBPP_PARSTATUS']
    if unpack_status_value == '0' and par_status_value == '0':
        # Unpack was skipped due to nzb-file properties
        # or due to errors during par-check
        if int(os.environ['NZBPP_HEALTH']) < 1000:
            logger.warning('Download health is compromised and Par-check/repair disabled or no .par2 files found. Setting status \'failed\'')
            status = 1
        else:
            logger.info('Par-check/repair disabled or no .par2 files found, and Unpack not required. Health is ok so handle as though download successful')
        logger.info('Please check your Par-check/repair settings for future downloads.')
    return status


def parse_status():
    if 'NZBPP_TOTALSTATUS' in os.environ:  # Called from nzbget 13.0 or later
        status = _parse_total_status()
    else:
        par_status = _parse_par_status()
        unpack_status = _parse_unpack_status()
        health_status = _parse_health_status()
        status = par_status or unpack_status or health_status
    return status


def check_version():
    """Check nzbget version and if version is unsupported, exit."""
    version = os.environ['NZBOP_VERSION']
    # Check if the script is called from nzbget 11.0 or later
    if version[0:5] < '11.0':
        logger.error('NZBGet Version {0} is not supported. Please update NZBGet.'.format(version))
        sys.exit(core.NZBGET_POSTPROCESS_ERROR)
    logger.info('Script triggered from NZBGet Version {0}.'.format(version))


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
