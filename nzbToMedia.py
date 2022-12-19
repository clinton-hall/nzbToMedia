import logging
import os
import sys

import nzb2media
from nzb2media.processor import nzbget, sab, manual
from nzb2media.processor.nzb import process
from nzb2media.auto_process.common import ProcessResult

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


def main(args, section=None):
    # Initialize the config
    nzb2media.initialize(section)

    log.info('#########################################################')
    log.info(f'## ..::[{os.path.basename(__file__)}]::.. ##')
    log.info('#########################################################')

    # debug command line options
    log.debug(f'Options passed into nzbToMedia: {args}')

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
        log.info('Script triggered from generic program')
        result = process(args[1], input_name=args[2], input_category=args[3], download_id=args[4])
    elif nzb2media.NZB_NO_MANUAL:
        log.warning('Invalid number of arguments received from client, and no_manual set')
    else:
        manual.process()

    if result.status_code == 0:
        log.info(f'The {args[0]} script completed successfully.')
        if result.message:
            print(result.message + '!')
        if 'NZBOP_SCRIPTDIR' in os.environ:  # return code for nzbget v11
            del nzb2media.MYAPP
            return nzb2media.NZBGET_POSTPROCESS_SUCCESS
    else:
        log.error(f'A problem was reported in the {args[0]} script.')
        if result.message:
            print(result.message + '!')
        if 'NZBOP_SCRIPTDIR' in os.environ:  # return code for nzbget v11
            del nzb2media.MYAPP
            return nzb2media.NZBGET_POSTPROCESS_ERROR
    del nzb2media.MYAPP
    return result.status_code


if __name__ == '__main__':
    sys.exit(main(sys.argv))
