import urllib
import core
import requests
from core import logger

def autoFork(section, inputCategory):
    # auto-detect correct section
    # config settings
    try:
        host = core.CFG[section][inputCategory]["host"]
        port = core.CFG[section][inputCategory]["port"]
    except:
        host = None
        port = None

    try:
        username = core.CFG[section][inputCategory]["username"]
        password = core.CFG[section][inputCategory]["password"]
    except:
        username = None
        password = None

    try:
        apikey = core.CFG[section][inputCategory]["apikey"]
    except:
        apikey = None

    try:
        ssl = int(core.CFG[section][inputCategory]["ssl"])
    except:
        ssl = 0

    try:
        web_root = core.CFG[section][inputCategory]["web_root"]
    except:
        web_root = ""

    try:
        fork = core.FORKS.items()[core.FORKS.keys().index(core.CFG[section][inputCategory]["fork"])]
    except:
        fork = "auto"

    if ssl:
        protocol = "https://"
    else:
        protocol = "http://"

    detected = False
    if section == "NzbDrone":
        logger.info("Attempting to verify %s fork" % inputCategory)
        url = "%s%s:%s%s/api/rootfolder" % (protocol,host,port,web_root)
        headers={"X-Api-Key": apikey}
        try:
            r = requests.get(url, headers=headers, stream=True, verify=False)
        except requests.ConnectionError:
            logger.warning("Could not connect to %s:%s to verify fork!" % (section, inputCategory))
            
        if not r.ok:
            logger.warning("Connection to %s:%s failed! Check your configuration" % (section, inputCategory))

        fork = ['default', {}]

    elif fork == "auto":
        params = core.ALL_FORKS
        rem_params = []
        logger.info("Attempting to auto-detect %s fork" % inputCategory)
        # define the order to test. Default must be first since the default fork doesn't reject parameters.
        # then in order of most unique parameters.
        url = "%s%s:%s%s/home/postprocess/" % (protocol,host,port,web_root)
        # attempting to auto-detect fork
        try:
            if username and password:
                s = requests.Session()
                login = "%s%s:%s%s/login" % (protocol,host,port,web_root)
                login_params = {'username': username, 'password': password}
                s.post(login, data=login_params, stream=True, verify=False)
                r = s.get(url, auth=(username, password), verify=False)
            else:
                r = requests.get(url, verify=False)
        except requests.ConnectionError:
            logger.info("Could not connect to %s:%s to perform auto-fork detection!" % (section, inputCategory))
            r = []
        if r and r.ok:
            for param in params:
                if not 'name="%s"' %(param) in r.text:
                    rem_params.append(param)
            for param in rem_params:
                params.pop(param) 
            for fork in sorted(core.FORKS.iteritems(), reverse=False):
                if params == fork[1]:
                    detected = True
                    break
        if detected:
            logger.info("%s:%s fork auto-detection successful ..." % (section, inputCategory))
        elif rem_params:
            logger.info("%s:%s fork auto-detection found custom params %s" % (section, inputCategory, params))
            fork = ['custom', params]
        else:
            logger.info("%s:%s fork auto-detection failed" % (section, inputCategory))
            fork = core.FORKS.items()[core.FORKS.keys().index(core.FORK_DEFAULT)]

    logger.info("%s:%s fork set to %s" % (section, inputCategory, fork[0]))
    return fork[0], fork[1]