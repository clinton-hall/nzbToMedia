import os

from core import logger
from core.processor import nzb


def process_script():
    client_agent = 'sabnzbd'
    logger.info('Script triggered from SABnzbd Version {0}.'.format(
        os.environ['SAB_VERSION']))
    return nzb.process(
        os.environ['SAB_COMPLETE_DIR'],
        input_name=os.environ['SAB_FINAL_NAME'],
        status=int(os.environ['SAB_PP_STATUS']),
        client_agent=client_agent,
        download_id=os.environ['SAB_NZO_ID'],
        input_category=os.environ['SAB_CAT'],
        failure_link=os.environ['SAB_FAILURE_URL'],
    )


def process_legacy(args):
    # SABnzbd argv:
    # 1 The final directory of the job (full path)
    # 2 The original name of the NZB file
    # 3 Clean version of the job name (no path info and '.nzb' removed)
    # 4 Indexer's report number (if supported)
    # 5 User-defined category
    # 6 Group that the NZB was posted in e.g. alt.binaries.x
    # 7 Status of post processing.
    #   0 = OK
    #   1 = failed verification
    #   2 = failed unpack
    #   3 = 1+2
    client_agent = 'sabnzbd'
    logger.info('Script triggered from SABnzbd')
    return nzb.process(
        args[1],
        input_name=args[2],
        status=int(args[7]),
        input_category=args[5],
        client_agent=client_agent,
        download_id='',
    )


def process_0717(args):
    # SABnzbd argv:
    # 1 The final directory of the job (full path)
    # 2 The original name of the NZB file
    # 3 Clean version of the job name (no path info and '.nzb' removed)
    # 4 Indexer's report number (if supported)
    # 5 User-defined category
    # 6 Group that the NZB was posted in e.g. alt.binaries.x
    # 7 Status of post processing. 0 = OK, 1=failed verification, 2=failed unpack, 3=1+2
    # 8 Failure URL
    client_agent = 'sabnzbd'
    logger.info('Script triggered from SABnzbd 0.7.17+')
    return nzb.process(
        args[1],
        input_name=args[2],
        status=int(args[7]),
        input_category=args[5],
        client_agent=client_agent,
        download_id='',
        failure_link=''.join(args[8:]),
    )
