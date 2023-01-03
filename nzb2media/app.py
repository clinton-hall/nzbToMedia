import argparse
import logging
import os

import nzb2media
import nzb2media.nzb
from nzb2media.auto_process.common import ProcessResult
from nzb2media.processor import nzbget, sab, manual
from nzb2media.processor.nzb import process

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())

parser = argparse.ArgumentParser()
parser.add_argument('args', nargs='*')


def main(argv: list[str] | None = None, section=None):
    # Initialize the config
    logging.basicConfig(
        level=logging.DEBUG,
        style='{',
        format='{asctime} | {levelname:<8} | {message}',
        datefmt='%Y-%m-%d %H:%M:%S',
    )
    parsed = parser.parse_args(argv)
    nzb2media.initialize(section)

    log.info('#########################################################')
    log.info('##               ..::[ nzbToMedia ]::..                ##')
    log.info('#########################################################')

    # debug command line options
    log.debug(f'Options passed into nzbToMedia: {parsed}')
    args = parsed.args

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
        result = process(
            input_directory=args[1],
            input_name=args[2],
            input_category=args[3],
            download_id=args[4],
        )
    elif nzb2media.nzb.NO_MANUAL:
        log.warning('Invalid number of arguments received from client, and no_manual set')
    else:
        manual.process()

    if not result.status_code:
        log.info(f'The {section or "nzbToMedia"} script completed successfully.')
        if result.message:
            print(result.message + '!')
        if 'NZBOP_SCRIPTDIR' in os.environ:  # return code for nzbget v11
            return nzbget.ExitCode.SUCCESS
    else:
        log.error(f'A problem was reported in the {args[0]} script.')
        if result.message:
            print(result.message + '!')
        if 'NZBOP_SCRIPTDIR' in os.environ:  # return code for nzbget v11
            return nzbget.ExitCode.FAILURE
    return result.status_code
