import os
import sys

import eol
import cleanup

eol.check()
cleanup.clean(cleanup.FOLDER_STRUCTURE)

import core
from core import logger
from core.processor import nzbget, sab, manual
from core.processor.nzb import process
from core.auto_process.common import ProcessResult


def main(args, section=None):
    # Initialize the config
    core.initialize(section)

    logger.info('#########################################################')
    logger.info(f'## ..::[{os.path.basename(__file__)}]::.. ##')
    logger.info('#########################################################')

    # debug command line options
    logger.debug(f'Options passed into nzbToMedia: {args}')

    # Post-Processing Result
    result = ProcessResult(
        message='',
        status_code=0,
    )

    # NZBGet
    if 'NZBOP_SCRIPTDIR' in os.environ:
        result = nzbget.process()
    # SABnzbd
    elif 'SAB_SCRIPT' in os.environ:
        result = sab.process_script()
    # SABnzbd Pre 0.7.17
    elif len(args) >= sab.MINIMUM_ARGUMENTS:
        result = sab.process(args)
    # Generic program
    elif len(args) > 5 and args[5] == 'generic':
        logger.info('Script triggered from generic program')
        result = process(args[1], input_name=args[2], input_category=args[3], download_id=args[4])
    elif core.NZB_NO_MANUAL:
        logger.warning('Invalid number of arguments received from client, and no_manual set')
    else:
        manual.process()

    if result.status_code == 0:
        logger.info(f'The {args[0]} script completed successfully.')
        if result.message:
            print(result.message + '!')
        if 'NZBOP_SCRIPTDIR' in os.environ:  # return code for nzbget v11
            del core.MYAPP
            return core.NZBGET_POSTPROCESS_SUCCESS
    else:
        logger.error(f'A problem was reported in the {args[0]} script.')
        if result.message:
            print(result.message + '!')
        if 'NZBOP_SCRIPTDIR' in os.environ:  # return code for nzbget v11
            del core.MYAPP
            return core.NZBGET_POSTPROCESS_ERROR
    del core.MYAPP
    return result.status_code


if __name__ == '__main__':
    exit(main(sys.argv))
