import requests

from core import logger


def command_complete(url, params, headers, section):
    try:
        r = requests.get(url, params=params, headers=headers, stream=True, verify=False, timeout=(30, 60))
    except requests.ConnectionError:
        logger.error("Unable to open URL: {0}".format(url), section)
        return None
    if r.status_code not in [requests.codes.ok, requests.codes.created, requests.codes.accepted]:
        logger.error("Server returned status {0}".format(r.status_code), section)
        return None
    else:
        try:
            return r.json()['state']
        except (ValueError, KeyError):
            # ValueError catches simplejson's JSONDecodeError and json's ValueError
            logger.error("{0} did not return expected json data.".format(section), section)
            return None


def completed_download_handling(url2, headers, section="MAIN"):
    try:
        r = requests.get(url2, params={}, headers=headers, stream=True, verify=False, timeout=(30, 60))
    except requests.ConnectionError:
        logger.error("Unable to open URL: {0}".format(url2), section)
        return False
    if r.status_code not in [requests.codes.ok, requests.codes.created, requests.codes.accepted]:
        logger.error("Server returned status {0}".format(r.status_code), section)
        return False
    else:
        try:
            return r.json().get("enableCompletedDownloadHandling", False)
        except ValueError:
            # ValueError catches simplejson's JSONDecodeError and json's ValueError
            return False
